import hashlib
import re
from datetime import UTC, datetime
from email.utils import parseaddr

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import Settings
from .models import AgentMessage, RecipientAlias, User
from .security import decrypt_json, encrypt_json

EMAIL_RE = re.compile(r"[\w.!#$%&'*+/=?^`{|}~-]+@[\w.-]+\.[A-Za-z]{2,}")
REMEMBER_WORDS = ("сохрани", "запомни", "на будущее", "remember", "save for later")
MISSING_PATTERNS = (
    re.compile(r"Не нашёл адрес для:\s*(.+?)\.\s*Укажите", re.IGNORECASE),
    re.compile(r"No address found for:\s*(.+?)\.\s*Provide", re.IGNORECASE),
)


def alias_context(user_id: str, normalized_name: str) -> str:
    return f"recipient:{user_id}:{normalized_name}"


def remembered_recipient_request(text: str, history: list[AgentMessage]) -> tuple[str, str] | None:
    if not any(word in text.casefold() for word in REMEMBER_WORDS):
        return None
    match = EMAIL_RE.search(text)
    if not match:
        return None
    email = parseaddr(match.group(0))[1].casefold()
    for message in reversed(history):
        if message.role != "assistant":
            continue
        for pattern in MISSING_PATTERNS:
            name_match = pattern.search(message.text)
            if name_match:
                return name_match.group(1).strip(), email
    return None


def save_recipient_alias(
    db: Session, settings: Settings, user: User, display_name: str, email: str
) -> RecipientAlias:
    normalized = " ".join(display_name.casefold().split())
    row = db.scalar(
        select(RecipientAlias).where(
            RecipientAlias.user_id == user.id,
            RecipientAlias.normalized_name == normalized,
        )
    )
    if row is None:
        row = RecipientAlias(user_id=user.id, normalized_name=normalized)
        db.add(row)
    row.display_name = display_name.strip()
    row.email_hash = hashlib.sha256(email.casefold().encode()).hexdigest()
    row.encrypted_email = encrypt_json(
        settings, {"email": email.casefold()}, alias_context(user.id, normalized)
    )
    row.updated_at = datetime.now(UTC)
    db.flush()
    return row


def find_recipient_alias(
    db: Session, settings: Settings, user: User, display_name: str
) -> str | None:
    normalized = " ".join(display_name.casefold().split())
    row = db.scalar(
        select(RecipientAlias).where(
            RecipientAlias.user_id == user.id,
            RecipientAlias.normalized_name == normalized,
        )
    )
    if row is None:
        return None
    return decrypt_json(
        settings, row.encrypted_email, alias_context(user.id, normalized)
    ).get("email")
