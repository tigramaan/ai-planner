from sqlalchemy import select

from app.database import SessionLocal
from app.models import FamilyInvite


def test_member_creates_unlimited_single_use_registration_links(logged_in):
    created = logged_in.post("/api/v1/family/invites")
    assert created.status_code == 201
    token = created.json()["invite_url"].split("invite=", 1)[1]

    registered = logged_in.post(
        "/api/v1/auth/register",
        json={
            "email": "friend@example.com",
            "password": "friend-strong-password",
            "invite_token": token,
        },
    )
    assert registered.status_code == 201
    second_invite = logged_in.post("/api/v1/family/invites")
    assert second_invite.status_code == 201
    assert second_invite.json()["invite_url"] != created.json()["invite_url"]
    reused = logged_in.post(
        "/api/v1/auth/register",
        json={
            "email": "other@example.com",
            "password": "other-strong-password",
            "invite_token": token,
        },
    )
    assert reused.status_code == 403
    with SessionLocal() as db:
        assert db.scalar(select(FamilyInvite)).used_at is not None


def test_non_admin_can_create_invites(client):
    registered = client.post(
        "/api/v1/auth/register",
        json={
            "email": "member@example.com",
            "password": "member-strong-password",
            "registration_code": "family-registration-code-2026",
        },
    )
    assert registered.status_code == 201
    assert client.post("/api/v1/family/invites").status_code == 201
