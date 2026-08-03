import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..audit import audit
from ..config import Settings, get_settings
from ..database import get_db
from ..dependencies import current_user
from ..models import FamilyInvite, User, UserSession
from ..schemas import (
    ChangePasswordRequest,
    InitialSetupRequest,
    LoginRequest,
    RegisterRequest,
    UserView,
)
from ..security import (
    client_ip,
    create_access_token,
    hash_password,
    new_refresh_token,
    token_hash,
    verify_password,
)

router = APIRouter(prefix="/api/v1", tags=["auth"])


@router.get("/auth/setup-status")
def setup_status(db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    configured = db.scalar(select(User).where(User.email == str(settings.owner_email))) is not None
    return {"setup_required": not configured}


@router.post("/auth/setup", response_model=UserView, status_code=201)
def initial_setup(
    body: InitialSetupRequest,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    email = str(settings.owner_email).casefold()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Initial setup is already complete")
    if not settings.initial_setup_token or not secrets.compare_digest(
        body.setup_token, settings.initial_setup_token
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid setup token")
    user = User(email=email, password_hash=hash_password(body.password), is_admin=True)
    db.add(user)
    db.flush()
    refresh_value = new_refresh_token()
    session = UserSession(
        user_id=user.id,
        refresh_token_hash=token_hash(refresh_value),
        device_name=body.device_name,
        ip=client_ip(request),
        expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_days),
    )
    db.add(session)
    audit(db, user, request, "auth.initial_setup", "user", user.id)
    db.commit()
    set_auth_cookies(
        response, settings, create_access_token(settings, user.id, session.id), refresh_value
    )
    return user


def set_auth_cookies(response: Response, settings: Settings, access: str, refresh: str) -> None:
    common = {"httponly": True, "secure": settings.cookie_secure, "samesite": "strict", "path": "/"}
    response.set_cookie(
        "access_token", access, max_age=settings.access_token_minutes * 60, **common
    )
    response.set_cookie(
        "refresh_token", refresh, max_age=settings.refresh_token_days * 86400, **common
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")


@router.post("/auth/login", response_model=UserView)
def login(
    body: LoginRequest,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    user = db.scalar(select(User).where(User.email == str(body.email).casefold()))
    if not user or not verify_password(user.password_hash, body.password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    refresh = new_refresh_token()
    session = UserSession(
        user_id=user.id,
        refresh_token_hash=token_hash(refresh),
        device_name=body.device_name,
        ip=client_ip(request),
        expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_days),
    )
    db.add(session)
    db.flush()
    user.last_login_at = datetime.now(UTC)
    audit(db, user, request, "auth.login", "session", session.id)
    db.commit()
    set_auth_cookies(
        response, settings, create_access_token(settings, user.id, session.id), refresh
    )
    return user


@router.post("/auth/register", response_model=UserView, status_code=201)
def register(
    body: RegisterRequest,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    invite = None
    if body.invite_token:
        invite = db.scalar(
            select(FamilyInvite)
            .where(FamilyInvite.token_hash == token_hash(body.invite_token))
            .with_for_update()
        )
    now = datetime.now(UTC)
    valid_invite = bool(
        invite and invite.used_at is None and invite.expires_at.replace(tzinfo=UTC) > now
    )
    valid_legacy_code = bool(
        body.registration_code
        and settings.family_registration_code
        and secrets.compare_digest(body.registration_code, settings.family_registration_code)
    )
    if not valid_invite and not valid_legacy_code:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Registration is invitation-only")
    email = str(body.email).casefold()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Account already exists")
    user = User(email=email, password_hash=hash_password(body.password))
    db.add(user)
    db.flush()
    refresh_value = new_refresh_token()
    session = UserSession(
        user_id=user.id,
        refresh_token_hash=token_hash(refresh_value),
        device_name=body.device_name,
        ip=client_ip(request),
        expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_days),
    )
    db.add(session)
    if invite:
        invite.used_at = now
    audit(db, user, request, "auth.register", "user", user.id)
    db.commit()
    set_auth_cookies(
        response, settings, create_access_token(settings, user.id, session.id), refresh_value
    )
    return user


@router.post("/auth/refresh", response_model=UserView)
def refresh(
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    raw = request.cookies.get("refresh_token", "")
    session = (
        db.scalar(select(UserSession).where(UserSession.refresh_token_hash == token_hash(raw)))
        if raw
        else None
    )
    now = datetime.now(UTC)
    if not session or session.revoked_at or session.expires_at.replace(tzinfo=UTC) <= now:
        clear_auth_cookies(response)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh session expired")
    user = db.get(User, session.user_id)
    # Keep the high-entropy refresh token stable during normal renewal. Rotating it here
    # makes simultaneous requests from several tabs invalidate each other.
    session.expires_at = now + timedelta(days=settings.refresh_token_days)
    db.commit()
    set_auth_cookies(
        response, settings, create_access_token(settings, user.id, session.id), raw
    )
    return user


@router.post("/auth/logout", status_code=204)
def logout(response: Response, request: Request, db: Session = Depends(get_db)):
    raw = request.cookies.get("refresh_token", "")
    session = (
        db.scalar(select(UserSession).where(UserSession.refresh_token_hash == token_hash(raw)))
        if raw
        else None
    )
    if session:
        session.revoked_at = datetime.now(UTC)
        db.commit()
    clear_auth_cookies(response)


@router.post("/auth/change-password", status_code=204)
def change_password(
    body: ChangePasswordRequest,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(user.password_hash, body.current_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect")
    if secrets.compare_digest(body.current_password, body.new_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "New password must be different")
    user.password_hash = hash_password(body.new_password)
    db.execute(
        update(UserSession)
        .where(UserSession.user_id == user.id)
        .values(revoked_at=datetime.now(UTC))
    )
    audit(db, user, request, "auth.password_changed", "user", user.id)
    db.commit()


@router.get("/me", response_model=UserView)
def me(user: User = Depends(current_user)):
    return user
