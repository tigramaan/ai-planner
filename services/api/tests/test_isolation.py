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

    register(client, "first@example.com")
    first_task = client.post("/api/v1/tasks", json={"title": "Только для первого"})
    assert first_task.status_code == 200
    assert (
        client.post(
            "/api/v1/timers", json={"title": "Личный таймер", "duration_seconds": 60}
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/integrations/openai",
            json={"api_key": "sk-first-users-private-key", "model": "gpt-test"},
        ).status_code
        == 200
    )

    register(client, "second@example.com")
    assert client.get("/api/v1/tasks").json() == []
    task_path = f"/api/v1/tasks/{first_task.json()['id']}"
    assert client.put(task_path, json={"status": "completed"}).status_code == 404
    assert client.delete(task_path).status_code == 404
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
    assert client.get("/api/v1/audit").json()[0]["action"] == "auth.register"
    assert client.get("/api/v1/today").json()["items"] == []
