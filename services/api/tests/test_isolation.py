def register(client, email):
    client.cookies.clear()
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "family-member-strong-password",
            "registration_code": "family-registration-code-2026",
        },
    )
    assert response.status_code == 201


def test_planner_and_integrations_are_isolated_per_user(client):
    from app.config import get_settings
    from app.database import SessionLocal
    from app.models import PendingAction, User
    from app.policy import create_pending_action

    register(client, "first@example.com")
    first_task = client.post("/api/v1/tasks", json={"title": "Только для первого"})
    assert first_task.status_code == 200
    first_timer = client.post(
        "/api/v1/timers", json={"title": "Личный таймер", "duration_seconds": 60}
    )
    assert first_timer.status_code == 200
    assert (
        client.post(
            "/api/v1/integrations/openai",
            json={"api_key": "sk-first-users-private-key", "model": "gpt-test"},
        ).status_code
        == 200
    )
    first_preferences = {
        "default_calendar": "microsoft",
        "default_mail": "microsoft",
        "default_conference": "microsoft",
        "default_reminder_minutes": 17,
        "fallback_teams_url": "https://teams.microsoft.com/l/meetup-join/private-room",
        "fallback_telemost_url": "https://telemost.yandex.ru/j/private-room",
    }
    assert client.put("/api/v1/preferences", json=first_preferences).status_code == 200
    with SessionLocal() as db:
        first = db.query(User).filter(User.email == "first@example.com").one()
        action = create_pending_action(
            db,
            get_settings(),
            first,
            "send_email",
            "Private draft",
            {"provider": "google", "to": ["private@example.com"], "subject": "Private"},
        )
        db.commit()
        first_action_id = action.id

    register(client, "second@example.com")
    assert client.get("/api/v1/tasks").json() == []
    task_path = f"/api/v1/tasks/{first_task.json()['id']}"
    assert client.put(task_path, json={"status": "completed"}).status_code == 404
    assert client.delete(task_path).status_code == 404
    timer_path = f"/api/v1/timers/{first_timer.json()['id']}"
    assert client.put(timer_path, json={"duration_seconds": 120}).status_code == 404
    assert client.delete(timer_path).status_code == 404
    assert client.post(f"/api/v1/pending-actions/{first_action_id}/confirm").status_code == 404
    assert client.post(f"/api/v1/pending-actions/{first_action_id}/cancel").status_code == 404
    integrations = client.get("/api/v1/integrations").json()
    server_fallback = [
        {
            "provider": "openai",
            "status": "connected",
            "scopes": [],
            "configured": True,
            "source": "server",
        }
    ]
    assert integrations == (server_fallback if get_settings().openai_api_key else [])
    assert "api_key" not in str(integrations)
    assert client.get("/api/v1/reminders").json() == []
    assert client.get("/api/v1/chat/messages").json() == []
    assert client.get("/api/v1/pending-actions").json() == []
    second_preferences = client.get("/api/v1/preferences").json()
    assert second_preferences["default_calendar"] == "google"
    assert second_preferences["default_reminder_minutes"] == 5
    assert second_preferences["fallback_teams_url"] == ""
    assert second_preferences["fallback_telemost_url"] == ""
    assert client.get("/api/v1/audit").json()[0]["action"] == "auth.register"
    assert client.get("/api/v1/today").json()["items"] == []
    with SessionLocal() as db:
        assert db.get(PendingAction, first_action_id).cancelled_at is None


def test_access_token_subject_must_own_its_session(client):
    from sqlalchemy import select

    from app.config import get_settings
    from app.database import SessionLocal
    from app.models import User, UserSession
    from app.security import create_access_token

    register(client, "session-first@example.com")
    with SessionLocal() as db:
        first = db.scalar(select(User).where(User.email == "session-first@example.com"))
        first_session = db.scalar(select(UserSession).where(UserSession.user_id == first.id))
    register(client, "session-second@example.com")
    with SessionLocal() as db:
        second = db.scalar(select(User).where(User.email == "session-second@example.com"))
    mismatched = create_access_token(get_settings(), second.id, first_session.id)
    client.cookies.set("access_token", mismatched)
    assert client.get("/api/v1/me").status_code == 401
