from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import Settings
from .models import User
from .security import hash_password


def ensure_owner(db: Session, settings: Settings) -> None:
    if db.scalar(select(User).where(User.email == str(settings.owner_email))):
        return
    if not settings.owner_initial_password:
        if not settings.initial_setup_token:
            raise RuntimeError(
                "OWNER_INITIAL_PASSWORD or INITIAL_SETUP_TOKEN is required for first startup"
            )
        return
    db.add(
        User(
            email=str(settings.owner_email),
            password_hash=hash_password(settings.owner_initial_password),
            is_admin=True,
        )
    )
    db.commit()
