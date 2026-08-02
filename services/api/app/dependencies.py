from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .config import Settings, get_settings
from .database import get_db
from .models import User, UserSession
from .security import decode_access_token


def current_user(
    access_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    if not access_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
    payload = decode_access_token(settings, access_token)
    session = db.get(UserSession, payload["sid"])
    if not session or session.revoked_at is not None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session revoked")
    user = db.get(User, payload["sub"])
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unknown session user")
    return user
