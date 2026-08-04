from sqlalchemy import select

from app.adapters import ProviderError
from app.database import SessionLocal
from app.models import Integration, User
from app.oauth import create_state, resolve_scopes
from app.routers import integrations as integrations_router


def google_state() -> str:
    with SessionLocal() as db:
        user = db.scalar(select(User))
        return create_state(
            db,
            user,
            "google",
            resolve_scopes("google", ["identity", "gmail.read"]),
        )


def test_google_decline_returns_to_settings_with_guidance(logged_in):
    response = logged_in.get(
        "/api/v1/integrations/google/oauth/callback",
        params={"state": google_state(), "error": "access_denied"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"].endswith("/settings?oauth_error=gmail_access_denied")


def test_google_gmail_is_verified_before_connection(logged_in, monkeypatch):
    async def tokens(*_args):
        return {
            "access_token": "access",
            "refresh_token": "refresh",
            "scope": "openid email https://www.googleapis.com/auth/gmail.readonly",
        }

    async def profile(*_args):
        return {"email": "family@example.com"}

    async def rejected(*_args):
        raise ProviderError("Provider request failed (403)", 403, "forbidden")

    monkeypatch.setattr(integrations_router, "exchange_code", tokens)
    monkeypatch.setattr(integrations_router, "account_profile", profile)
    monkeypatch.setattr(integrations_router, "verify_google_gmail_access", rejected)

    response = logged_in.get(
        "/api/v1/integrations/google/oauth/callback",
        params={"state": google_state(), "code": "code"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"].endswith(
        "/settings?oauth_error=gmail_mailbox_unavailable"
    )
    with SessionLocal() as db:
        assert db.scalar(select(Integration).where(Integration.provider == "google")) is None


def test_google_missing_requested_scope_is_rejected(logged_in, monkeypatch):
    async def incomplete_tokens(*_args):
        return {"access_token": "access", "scope": "openid email"}

    monkeypatch.setattr(integrations_router, "exchange_code", incomplete_tokens)
    response = logged_in.get(
        "/api/v1/integrations/google/oauth/callback",
        params={"state": google_state(), "code": "code"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"].endswith("/settings?oauth_error=gmail_access_denied")
