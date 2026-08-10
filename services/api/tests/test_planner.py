from sqlalchemy import select

from app.agenda import provider_event
from app.database import SessionLocal
from app.models import Reminder


def test_tasks_are_in_agenda_but_timers_are_chat_only(logged_in):
    task = logged_in.post("/api/v1/tasks", json={"title": "Подготовить план"})
    assert task.status_code == 200
    assert task.json()["title"] == "Подготовить план"
    timer = logged_in.post("/api/v1/timers", json={"title": "Фокус", "duration_seconds": 1500})
    assert timer.status_code == 200
    with SessionLocal() as db:
        reminder = db.scalar(select(Reminder).where(Reminder.timer_id == timer.json()["id"]))
        assert reminder is not None
        assert reminder.due_at == reminder.next_attempt_at
        assert "Фокус" in reminder.title
    today = logged_in.get("/api/v1/today")
    assert today.status_code == 200
    assert {item["kind"] for item in today.json()["items"]} == {"task"}
    week = logged_in.get("/api/v1/week")
    assert week.status_code == 200
    assert {item["kind"] for item in week.json()["items"]} == {"task"}


def test_task_can_be_edited_completed_reopened_and_deleted(logged_in):
    created = logged_in.post(
        "/api/v1/tasks", json={"title": "Черновик", "priority": "normal"}
    )
    task_id = created.json()["id"]
    updated = logged_in.put(
        f"/api/v1/tasks/{task_id}",
        json={
            "title": "Подготовить договор",
            "description": "Проверить приложение",
            "due_at": "2026-08-05T12:00:00+03:00",
            "timezone": "Europe/Moscow",
            "priority": "high",
            "status": "completed",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Подготовить договор"
    assert updated.json()["priority"] == "high"
    assert updated.json()["status"] == "completed"
    archived = logged_in.get("/api/v1/tasks")
    assert archived.status_code == 200
    assert any(
        row["id"] == task_id and row["status"] == "completed"
        for row in archived.json()
    )
    assert logged_in.put(f"/api/v1/tasks/{task_id}", json={"title": None}).status_code == 422

    reopened = logged_in.put(
        f"/api/v1/tasks/{task_id}", json={"status": "open", "due_at": None}
    )
    assert reopened.status_code == 200
    assert reopened.json()["status"] == "open"
    assert reopened.json()["due_at"] is None

    assert logged_in.delete(f"/api/v1/tasks/{task_id}").status_code == 204
    assert (
        logged_in.put(f"/api/v1/tasks/{task_id}", json={"status": "open"}).status_code
        == 404
    )


def test_due_task_notification_follows_task_lifecycle(logged_in):
    created = logged_in.post(
        "/api/v1/tasks",
        json={
            "title": "Отправить отчёт",
            "due_at": "2099-08-05T18:00:00+03:00",
            "timezone": "Europe/Moscow",
        },
    )
    task_id = created.json()["id"]
    with SessionLocal() as db:
        reminder = db.scalar(select(Reminder).where(Reminder.task_id == task_id))
        assert reminder is not None
        original_due = reminder.due_at
        assert "Отправить отчёт" in reminder.title

    renamed = logged_in.put(
        f"/api/v1/tasks/{task_id}", json={"title": "Отправить итоговый отчёт"}
    )
    assert renamed.status_code == 200
    with SessionLocal() as db:
        reminder = db.scalar(select(Reminder).where(Reminder.task_id == task_id))
        assert reminder.due_at == original_due
        assert "итоговый" in reminder.title

    completed = logged_in.put(
        f"/api/v1/tasks/{task_id}", json={"status": "completed"}
    )
    assert completed.status_code == 200
    with SessionLocal() as db:
        assert db.scalar(select(Reminder).where(Reminder.task_id == task_id)) is None

    reopened = logged_in.put(f"/api/v1/tasks/{task_id}", json={"status": "open"})
    assert reopened.status_code == 200
    with SessionLocal() as db:
        assert db.scalar(select(Reminder).where(Reminder.task_id == task_id)) is not None

    assert logged_in.delete(f"/api/v1/tasks/{task_id}").status_code == 204
    with SessionLocal() as db:
        assert db.scalar(select(Reminder).where(Reminder.task_id == task_id)) is None


def test_timer_can_be_restarted_renamed_and_deleted(logged_in):
    created = logged_in.post(
        "/api/v1/timers", json={"title": "Фокус", "duration_seconds": 300}
    )
    timer_id = created.json()["id"]
    updated = logged_in.put(
        f"/api/v1/timers/{timer_id}",
        json={"title": "Перерыв", "duration_seconds": 600},
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Перерыв"
    assert updated.json()["status"] == "active"
    with SessionLocal() as db:
        reminder = db.scalar(select(Reminder).where(Reminder.timer_id == timer_id))
        assert reminder is not None
        assert "Перерыв" in reminder.title
        assert reminder.status == "scheduled"
    assert logged_in.delete(f"/api/v1/timers/{timer_id}").status_code == 204
    with SessionLocal() as db:
        assert db.scalar(select(Reminder).where(Reminder.timer_id == timer_id)) is None
    assert logged_in.delete(f"/api/v1/timers/{timer_id}").status_code == 404


def test_active_timers_are_listed_with_names_and_end_times(logged_in):
    first = logged_in.post(
        "/api/v1/timers", json={"title": "Макароны", "duration_seconds": 600}
    ).json()
    second = logged_in.post(
        "/api/v1/timers", json={"title": "Яйца", "duration_seconds": 420}
    ).json()
    rows = logged_in.get("/api/v1/timers")
    assert rows.status_code == 200
    assert {row["title"] for row in rows.json()} >= {"Макароны", "Яйца"}
    assert all(row["ends_at"] for row in rows.json())
    assert {first["id"], second["id"]} <= {row["id"] for row in rows.json()}


def test_google_agenda_event_keeps_time_links_attendees_and_reminder():
    item = provider_event("google", {
        "id": "event-1", "summary": "Встреча", "status": "confirmed",
        "start": {"dateTime": "2026-08-03T15:30:00+03:00"},
        "end": {"dateTime": "2026-08-03T16:00:00+03:00"},
        "attendees": [{"email": "guest@example.com"}],
        "location": "https://telemost.yandex.ru/j/123",
        "htmlLink": "https://calendar.google.com/event/1",
        "reminders": {"overrides": [{"method": "popup", "minutes": 5}]},
    })
    assert item["join_url"] == "https://telemost.yandex.ru/j/123"
    assert item["edit_url"].startswith("https://calendar.google.com/")
    assert item["attendees"] == ["guest@example.com"]
    assert item["reminder_minutes"] == 5


def test_requires_login(client):
    for path in ("/api/v1/tasks", "/api/v1/today", "/api/v1/week", "/api/v1/integrations", "/api/v1/audit"):
        assert client.get(path).status_code == 401
