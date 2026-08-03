from datetime import UTC, datetime, timedelta

WORKER_HEADERS = {"X-Worker-Token": "test-worker-service-token-that-is-long-enough"}


def test_reminder_claim_delivery_and_encrypted_push(logged_in):
    assert logged_in.get("/api/v1/push/status").json() == {"configured": False}
    subscription = logged_in.post(
        "/api/v1/push/subscriptions",
        json={
            "endpoint": "https://push.example.com/private-device-token",
            "p256dh": "public-encryption-key-material",
            "auth": "authentication-secret",
        },
    )
    assert subscription.status_code == 201
    assert "endpoint" not in subscription.text
    assert logged_in.get("/api/v1/push/status").json() == {"configured": True}
    due = datetime.now(UTC) - timedelta(seconds=1)
    created = logged_in.post(
        "/api/v1/reminders",
        json={
            "title": "Проверить напоминание",
            "due_at": due.isoformat(),
            "timezone": "UTC",
            "channel": "push",
        },
    )
    assert created.status_code == 200
    reminder_id = created.json()["id"]
    assert logged_in.post("/internal/v1/reminders/claim").status_code == 401
    claimed = logged_in.post("/internal/v1/reminders/claim", headers=WORKER_HEADERS)
    assert claimed.status_code == 200
    row = claimed.json()[0]
    assert row["id"] == reminder_id
    assert row["subscriptions"][0]["endpoint"].startswith("https://push.example.com/")
    completed = logged_in.post(
        f"/internal/v1/reminders/{reminder_id}/complete",
        headers=WORKER_HEADERS,
        json={"status": "delivered"},
    )
    assert completed.status_code == 204
    reminders = logged_in.get("/api/v1/reminders").json()
    assert reminders[0]["status"] == "delivered"


def test_reminder_requires_timezone_offset(logged_in):
    response = logged_in.post(
        "/api/v1/reminders",
        json={"title": "Некорректное время", "due_at": "2026-08-03T12:00:00"},
    )
    assert response.status_code == 422


def test_push_public_key_requires_login_only_for_subscription(client, logged_in):
    assert client.get("/api/v1/push/public-key").status_code == 200
    assert logged_in.get("/api/v1/push/public-key").json()["public_key"]
