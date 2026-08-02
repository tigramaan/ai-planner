import hashlib
import json
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from .config import Settings
from .models import PendingAction, User
from .security import encrypt_json


def create_pending_action(
    db: Session, settings: Settings, user: User, action_type: str, summary: str, payload: dict
) -> PendingAction:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    action = PendingAction(
        user_id=user.id,
        action_type=action_type,
        display_summary=summary,
        payload_hash=digest,
        payload_encrypted="",
        idempotency_key=secrets.token_hex(32),
        expires_at=datetime.now(UTC) + timedelta(minutes=30),
    )
    db.add(action)
    db.flush()
    action.payload_encrypted = encrypt_json(settings, payload, f"pending:{action.id}:{digest}")
    return action


def action_status(action: PendingAction) -> str:
    if action.cancelled_at:
        return "cancelled"
    if action.executed_at:
        return "executed"
    if action.confirmed_at:
        return "confirmed"
    if action.expires_at.replace(tzinfo=UTC) <= datetime.now(UTC):
        return "expired"
    return "pending"
