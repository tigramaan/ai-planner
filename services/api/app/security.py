import base64
import hashlib
import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import HTTPException, Request, status

from .config import Settings

password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, ValueError):
        return False


def token_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def create_access_token(settings: Settings, user_id: str, session_id: str) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "sid": session_id,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_access_token(settings: Settings, token: str) -> dict[str, Any]:
    if not settings.jwt_secret:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Authentication is not configured")
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid session") from exc
    if payload.get("type") != "access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid session")
    return payload


def new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def _master_key(settings: Settings) -> bytes:
    try:
        encoded = settings.secret_master_key.encode()
        key = base64.urlsafe_b64decode(encoded + b"=" * (-len(encoded) % 4))
    except Exception as exc:
        raise RuntimeError("SECRET_MASTER_KEY must be urlsafe base64") from exc
    if len(key) != 32:
        raise RuntimeError("SECRET_MASTER_KEY must decode to 32 bytes")
    return key


def encrypt_json(settings: Settings, payload: dict[str, Any], context: str) -> str:
    nonce = secrets.token_bytes(12)
    plaintext = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    ciphertext = AESGCM(_master_key(settings)).encrypt(nonce, plaintext, context.encode())
    return base64.urlsafe_b64encode(nonce + ciphertext).decode()


def decrypt_json(settings: Settings, encoded: str, context: str) -> dict[str, Any]:
    packed = base64.urlsafe_b64decode(encoded.encode())
    plaintext = AESGCM(_master_key(settings)).decrypt(packed[:12], packed[12:], context.encode())
    return json.loads(plaintext)


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    return forwarded or (request.client.host if request.client else "unknown")


SENSITIVE_KEYS = {"password", "token", "access_token", "refresh_token", "client_secret", "api_key"}


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[redacted]" if key.lower() in SENSITIVE_KEYS else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value
