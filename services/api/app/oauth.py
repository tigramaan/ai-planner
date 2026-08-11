import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import Settings
from .models import OAuthState, User
from .security import token_hash


class OAuthRefreshError(RuntimeError):
    def __init__(self, status_code: int | None):
        super().__init__("OAuth token refresh was rejected")
        self.status_code = status_code


GOOGLE_SCOPE_GROUPS = {
    "identity": ["openid", "email"],
    "calendar.read": ["https://www.googleapis.com/auth/calendar.readonly"],
    "calendar.write": ["https://www.googleapis.com/auth/calendar.events"],
    "contacts.read": ["https://www.googleapis.com/auth/contacts.readonly"],
    "gmail.read": ["https://www.googleapis.com/auth/gmail.readonly"],
    "gmail.compose": ["https://www.googleapis.com/auth/gmail.compose"],
    "gmail.send": ["https://www.googleapis.com/auth/gmail.send"],
}
MICROSOFT_SCOPE_GROUPS = {
    "identity": ["openid", "profile", "email", "offline_access", "User.Read"],
    "calendar": ["Calendars.ReadWrite"],
    "contacts": ["Contacts.Read"],
    "mail.read": ["Mail.Read"],
    "mail.write": ["Mail.ReadWrite", "Mail.Send"],
    "teams": ["OnlineMeetings.ReadWrite"],
}
ZOOM_SCOPE_GROUPS = {
    "identity": ["user:read:user"],
    "meeting": ["meeting:write:meeting"],
}


def resolve_scopes(provider: str, groups: list[str]) -> list[str]:
    source = (
        GOOGLE_SCOPE_GROUPS
        if provider == "google"
        else ZOOM_SCOPE_GROUPS
        if provider == "zoom"
        else MICROSOFT_SCOPE_GROUPS
    )
    selected = groups or (
        ["identity", "calendar.read", "calendar.write", "contacts.read"]
        if provider == "google"
        else ["identity", "meeting"]
        if provider == "zoom"
        else ["identity", "calendar", "contacts", "teams"]
    )
    unknown = set(selected) - set(source)
    if unknown:
        raise ValueError(f"Unsupported scope groups: {', '.join(sorted(unknown))}")
    return list(dict.fromkeys(scope for group in selected for scope in source[group]))


def create_state(db: Session, user: User, provider: str, scopes: list[str]) -> str:
    raw = secrets.token_urlsafe(32)
    db.add(
        OAuthState(
            state_hash=token_hash(raw),
            user_id=user.id,
            provider=provider,
            scopes=scopes,
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
        )
    )
    db.commit()
    return raw


def consume_state(db: Session, raw: str, provider: str) -> OAuthState:
    state = db.scalar(select(OAuthState).where(OAuthState.state_hash == token_hash(raw)))
    now = datetime.now(UTC)
    if (
        not state
        or state.provider != provider
        or state.used_at is not None
        or state.expires_at.replace(tzinfo=UTC) <= now
    ):
        raise ValueError("Invalid or expired OAuth state")
    state.used_at = now
    db.commit()
    return state


def authorization_url(settings: Settings, provider: str, state: str, scopes: list[str]) -> str:
    redirect = f"{settings.public_base_url}/api/v1/integrations/{provider}/oauth/callback"
    if provider == "google":
        base = "https://accounts.google.com/o/oauth2/v2/auth"
        params = {
            "client_id": settings.google_client_id,
            "redirect_uri": redirect,
            "response_type": "code",
            "scope": " ".join(scopes),
            "access_type": "offline",
            "include_granted_scopes": "true",
            "prompt": "consent",
            "state": state,
        }
    elif provider == "microsoft":
        base = (
            f"https://login.microsoftonline.com/{settings.microsoft_tenant}/oauth2/v2.0/authorize"
        )
        params = {
            "client_id": settings.microsoft_client_id,
            "redirect_uri": redirect,
            "response_type": "code",
            "response_mode": "query",
            "scope": " ".join(scopes),
            "state": state,
        }
    else:
        base = "https://zoom.us/oauth/authorize"
        params = {
            "client_id": settings.zoom_client_id,
            "redirect_uri": redirect,
            "response_type": "code",
            "state": state,
        }
    return f"{base}?{urlencode(params)}"


async def exchange_code(settings: Settings, provider: str, code: str, scopes: list[str]) -> dict:
    redirect = f"{settings.public_base_url}/api/v1/integrations/{provider}/oauth/callback"
    if provider == "google":
        url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect,
        }
    elif provider == "microsoft":
        url = f"https://login.microsoftonline.com/{settings.microsoft_tenant}/oauth2/v2.0/token"
        data = {
            "client_id": settings.microsoft_client_id,
            "client_secret": settings.microsoft_client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect,
            "scope": " ".join(scopes),
        }
    else:
        url = "https://zoom.us/oauth/token"
        data = {
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect,
        }
    async with httpx.AsyncClient(timeout=20) as client:
        auth = (
            httpx.BasicAuth(settings.zoom_client_id, settings.zoom_client_secret)
            if provider == "zoom"
            else None
        )
        response = await client.post(url, data=data, auth=auth)
    if response.status_code >= 400:
        raise RuntimeError(f"OAuth token exchange failed ({response.status_code})")
    payload = response.json()
    if not payload.get("access_token"):
        raise RuntimeError("OAuth provider returned no access token")
    return payload


async def refresh_access_token(
    settings: Settings, provider: str, refresh_token: str, scopes: list[str]
) -> dict:
    if provider == "google":
        url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
    elif provider == "microsoft":
        url = f"https://login.microsoftonline.com/{settings.microsoft_tenant}/oauth2/v2.0/token"
        data = {
            "client_id": settings.microsoft_client_id,
            "client_secret": settings.microsoft_client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "scope": " ".join(scopes),
        }
    else:
        url = "https://zoom.us/oauth/token"
        data = {"refresh_token": refresh_token, "grant_type": "refresh_token"}
    async with httpx.AsyncClient(timeout=20) as client:
        auth = (
            httpx.BasicAuth(settings.zoom_client_id, settings.zoom_client_secret)
            if provider == "zoom"
            else None
        )
        response = await client.post(url, data=data, auth=auth)
    if response.status_code >= 400:
        raise OAuthRefreshError(response.status_code)
    payload = response.json()
    if not payload.get("access_token"):
        raise OAuthRefreshError(None)
    return payload
