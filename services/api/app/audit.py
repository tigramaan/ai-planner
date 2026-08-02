from fastapi import Request
from sqlalchemy.orm import Session

from .models import AuditLog, User
from .security import client_ip, redact


def audit(
    db: Session,
    user: User,
    request: Request,
    action: str,
    target_type: str,
    target_id: str | None = None,
    details: dict | None = None,
) -> None:
    db.add(
        AuditLog(
            user_id=user.id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details_redacted_json=redact(details or {}),
            ip=client_ip(request),
        )
    )
