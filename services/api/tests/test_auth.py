from sqlalchemy import delete

from app.database import SessionLocal
from app.models import User


def test_health_and_owner_login(client):
    assert client.get("/health/live").json()["status"] == "ok"
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "tigramaan@gmail.com", "password": "correct-horse-battery-staple"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == "tigramaan@gmail.com"
    assert response.cookies.get("access_token")
    assert client.get("/api/v1/me").status_code == 200


def test_single_use_initial_setup(client):
    client.cookies.clear()
    with SessionLocal() as db:
        db.execute(delete(User))
        db.commit()
    setup = client.get("/api/v1/auth/setup-status").json()
    assert setup == {"setup_required": True}
    response = client.post(
        "/api/v1/auth/setup",
        json={
            "setup_token": "test-initial-setup-token-that-is-long-enough",
            "password": "new-owner-password-is-strong",
        },
    )
    assert response.status_code == 201
    assert response.json()["is_admin"] is True
    assert client.get("/api/v1/me").status_code == 200
    assert (
        client.post(
            "/api/v1/auth/setup",
            json={
                "setup_token": "test-initial-setup-token-that-is-long-enough",
                "password": "another-strong-owner-password",
            },
        ).status_code
        == 409
    )


def test_non_owner_and_bad_password_are_rejected(client):
    for email, password in [
        ("other@example.com", "correct-horse-battery-staple"),
        ("tigramaan@gmail.com", "bad"),
    ]:
        response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid credentials"


def test_family_registration_and_isolated_login(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "family@example.com",
            "password": "family-member-strong-password",
            "registration_code": "family-registration-code-2026",
        },
    )
    assert response.status_code == 201
    assert response.json()["email"] == "family@example.com"
    assert response.json()["is_admin"] is False
    assert client.get("/api/v1/me").status_code == 200


def test_expired_access_is_refreshed_without_ending_session(client):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "tigramaan@gmail.com", "password": "correct-horse-battery-staple"},
    )
    assert login.status_code == 200
    refresh_token = client.cookies.get("refresh_token")
    client.cookies.delete("access_token")

    refreshed = client.post("/api/v1/auth/refresh")

    assert refreshed.status_code == 200
    assert client.cookies.get("refresh_token") == refresh_token
    assert client.cookies.get("access_token")
    assert client.get("/api/v1/me").status_code == 200


def test_registration_requires_family_code(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "blocked@example.com",
            "password": "strong-password-for-member",
            "registration_code": "wrong",
        },
    )
    assert response.status_code == 403


def test_password_change_revokes_session(logged_in):
    response = logged_in.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": "correct-horse-battery-staple",
            "new_password": "a-completely-new-strong-password",
        },
    )
    assert response.status_code == 204
    assert logged_in.get("/api/v1/me").status_code == 401
    assert (
        logged_in.post(
            "/api/v1/auth/login",
            json={"email": "tigramaan@gmail.com", "password": "a-completely-new-strong-password"},
        ).status_code
        == 200
    )
