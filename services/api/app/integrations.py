from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import Settings
from .models import Integration, IntegrationSecret, User
from .oauth import OAuthRefreshError, refresh_access_token
from .security import decrypt_json, encrypt_json


def get_integration(db: Session, user: User, provider: str) -> Integration | None:
    return db.scalar(
        select(Integration).where(Integration.user_id == user.id, Integration.provider == provider)
    )


def upsert_secret(
    db: Session,
    settings: Settings,
    user: User,
    provider: str,
    payload: dict,
    scopes: list[str] | None = None,
    account_email: str | None = None,
) -> Integration:
    integration = get_integration(db, user, provider)
    if not integration:
        integration = Integration(user_id=user.id, provider=provider)
        db.add(integration)
        db.flush()
    context = f"integration:{integration.id}:{provider}"
    encoded = encrypt_json(settings, payload, context)
    if integration.secret:
        integration.secret.encrypted_payload = encoded
        integration.secret.rotated_at = datetime.now(UTC)
    else:
        integration.secret = IntegrationSecret(
            integration_id=integration.id, encrypted_payload=encoded
        )
    integration.status = "connected"
    integration.scopes = list(dict.fromkeys([*integration.scopes, *(scopes or [])]))
    integration.account_email = account_email or integration.account_email
    integration.connected_at = datetime.now(UTC)
    return integration


def read_secret(db: Session, settings: Settings, user: User, provider: str) -> dict:
    integration = get_integration(db, user, provider)
    if not integration or not integration.secret:
        raise LookupError(f"{provider} is not configured")
    return decrypt_json(
        settings, integration.secret.encrypted_payload, f"integration:{integration.id}:{provider}"
    )


def integration_view(integration: Integration) -> dict:
    return {
        "id": integration.id,
        "provider": integration.provider,
        "account_email": integration.account_email,
        "status": integration.status,
        "scopes": integration.scopes,
        "connected_at": integration.connected_at,
        "last_healthcheck_at": integration.last_healthcheck_at,
        "configured": integration.secret is not None,
    }


async def valid_access_token(db: Session, settings: Settings, user: User, provider: str) -> str:
    integration = get_integration(db, user, provider)
    secret = read_secret(db, settings, user, provider)
    expires_at = secret.get("expires_at")
    if not expires_at or datetime.fromisoformat(expires_at) > datetime.now(UTC):
        token = secret.get("access_token")
        if not token:
            raise LookupError(f"{provider} has no access token")
        return token
    refresh_token = secret.get("refresh_token")
    if not refresh_token:
        raise LookupError(f"{provider} authorization expired")
    try:
        refreshed = await refresh_access_token(
            settings, provider, refresh_token, integration.scopes if integration else []
        )
    except OAuthRefreshError as exc:
        if integration is not None:
            integration.status = "reauthorization_required"
            db.commit()
        raise LookupError(f"{provider} authorization must be renewed") from exc
    merged = {**secret, **refreshed, "refresh_token": refreshed.get("refresh_token", refresh_token)}
    if merged.get("expires_in"):
        merged["expires_at"] = (
            datetime.now(UTC) + timedelta(seconds=int(merged["expires_in"]))
        ).isoformat()
    upsert_secret(db, settings, user, provider, merged)
    db.commit()
    return merged["access_token"]
