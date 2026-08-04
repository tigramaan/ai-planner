from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.database import SessionLocal
from app.models import AgentMessage, PushSubscription, Reminder, Timer, User

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


def test_push_delivery_can_be_checked_from_the_browser(logged_in):
    endpoint = "https://push.example.com/test-device"
    assert logged_in.post("/api/v1/push/test", json={"endpoint": endpoint}).status_code == 409
    logged_in.post(
        "/api/v1/push/subscriptions",
        json={
            "endpoint": endpoint,
            "p256dh": "public-encryption-key-material",
            "auth": "authentication-secret",
        },
    )
    created = logged_in.post("/api/v1/push/test", json={"endpoint": endpoint})
    assert created.status_code == 202
    reminder_id = created.json()["id"]
    assert logged_in.get(f"/api/v1/push/test/{reminder_id}").json()["device_status"] == "scheduled"
    claimed = logged_in.post("/internal/v1/reminders/claim", headers=WORKER_HEADERS).json()
    subscription_id = claimed[0]["subscriptions"][0]["id"]
    logged_in.post(
        f"/internal/v1/reminders/{reminder_id}/complete",
        headers=WORKER_HEADERS,
        json={
            "status": "delivered",
            "deliveries": [
                {
                    "subscription_id": subscription_id,
                    "status": "delivered",
                    "status_code": 201,
                }
            ],
        },
    )
    result = logged_in.get(f"/api/v1/push/test/{reminder_id}").json()
    assert result == {
        "status": "delivered",
        "device_status": "delivered",
        "provider": "push.example.com",
        "status_code": 201,
    }


def test_push_retries_only_failed_device_and_removes_stale_subscription(logged_in):
    endpoints = ["https://push.example.com/accepted", "https://web.push.apple.com/stale"]
    for endpoint in endpoints:
        response = logged_in.post(
            "/api/v1/push/subscriptions",
            json={
                "endpoint": endpoint,
                "p256dh": "public-encryption-key-material",
                "auth": "authentication-secret",
            },
        )
        assert response.status_code == 201
    due = datetime.now(UTC) - timedelta(seconds=1)
    reminder_id = logged_in.post(
        "/api/v1/reminders",
        json={"title": "Два устройства", "due_at": due.isoformat(), "channel": "push"},
    ).json()["id"]
    first_claim = logged_in.post(
        "/internal/v1/reminders/claim", headers=WORKER_HEADERS
    ).json()[0]
    subscription_ids = {
        row["endpoint"]: row["id"] for row in first_claim["subscriptions"]
    }
    completed = logged_in.post(
        f"/internal/v1/reminders/{reminder_id}/complete",
        headers=WORKER_HEADERS,
        json={
            "status": "retry",
            "deliveries": [
                {
                    "subscription_id": subscription_ids[endpoints[0]],
                    "status": "delivered",
                    "status_code": 201,
                },
                {
                    "subscription_id": subscription_ids[endpoints[1]],
                    "status": "retry",
                    "status_code": 503,
                    "error": "push:503",
                },
            ],
        },
    )
    assert completed.status_code == 204
    with SessionLocal() as db:
        reminder = db.get(Reminder, reminder_id)
        reminder.next_attempt_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
    second_claim = logged_in.post(
        "/internal/v1/reminders/claim", headers=WORKER_HEADERS
    ).json()[0]
    assert [row["endpoint"] for row in second_claim["subscriptions"]] == [endpoints[1]]
    stale = logged_in.post(
        f"/internal/v1/reminders/{reminder_id}/complete",
        headers=WORKER_HEADERS,
        json={
            "status": "failed",
            "deliveries": [
                {
                    "subscription_id": subscription_ids[endpoints[1]],
                    "status": "stale",
                    "status_code": 410,
                    "error": "push:410",
                }
            ],
        },
    )
    assert stale.status_code == 204
    with SessionLocal() as db:
        assert db.get(Reminder, reminder_id).status == "delivered"
        remaining = db.scalars(select(PushSubscription)).all()
        assert [row.id for row in remaining] == [subscription_ids[endpoints[0]]]


def test_finished_named_timer_is_written_to_chat_history(logged_in):
    now = datetime.now(UTC)
    with SessionLocal() as db:
        user = db.scalar(select(User))
        timer = Timer(user_id=user.id, title="Макароны", ends_at=now)
        db.add(timer)
        db.flush()
        reminder = Reminder(
            user_id=user.id,
            timer_id=timer.id,
            title="Таймер «Макароны» завершён",
            due_at=now,
            next_attempt_at=now,
            timezone="Europe/Moscow",
            channel="push",
            status="processing",
            attempts=1,
        )
        db.add(reminder)
        db.commit()
        reminder_id = reminder.id
        timer_id = timer.id

    completed = logged_in.post(
        f"/internal/v1/reminders/{reminder_id}/complete",
        headers=WORKER_HEADERS,
        json={"status": "delivered"},
    )

    assert completed.status_code == 204
    with SessionLocal() as db:
        assert db.get(Timer, timer_id).status == "finished"
        message = db.scalar(select(AgentMessage).where(AgentMessage.text.contains("Макароны")))
        assert message is not None
        assert message.role == "assistant"
