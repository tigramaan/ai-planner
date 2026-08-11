from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app import integrations
from app.config import get_settings
from app.database import SessionLocal
from app.models import Integration, User
from app.oauth import OAuthRefreshError


@pytest.mark.anyio
async def test_rejected_refresh_requires_reauthorization(logged_in, monkeypatch):
    async def rejected(*args, **kwargs):
        raise OAuthRefreshError(400)

    monkeypatch.setattr(integrations, "refresh_access_token", rejected)
    with SessionLocal() as db:
        user = db.scalar(select(User))
        integrations.upsert_secret(
            db,
            get_settings(),
            user,
            "google",
            {
                "access_token": "expired",
                "refresh_token": "revoked",
                "expires_at": (datetime.now(UTC) - timedelta(minutes=1)).isoformat(),
            },
            ["https://www.googleapis.com/auth/calendar.events"],
        )
        db.commit()

        with pytest.raises(LookupError, match="authorization must be renewed"):
            await integrations.valid_access_token(db, get_settings(), user, "google")

        db.refresh(db.scalar(select(Integration).where(Integration.provider == "google")))
        integration = db.scalar(select(Integration).where(Integration.provider == "google"))
        assert integration.status == "reauthorization_required"
