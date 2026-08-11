from sqlalchemy import select

from app.database import SessionLocal
from app.models import LocalTask, Reminder, User
from app.routers import chat as chat_router
from app.schemas import Intent


def test_reminder_can_be_found_by_fragment_and_rescheduled(logged_in, monkeypatch):
    with SessionLocal() as db:
        user = db.scalar(select(User))
        db.add(
            Reminder(
                user_id=user.id,
                title="Отправить техзадание Роману в самолёт",
                due_at=user.created_at,
                next_attempt_at=user.created_at,
                timezone="Europe/Moscow",
                status="delivered",
                attempts=1,
            )
        )
        db.commit()

    async def intent(*args, **kwargs):
        return Intent(
            intent="update_reminder",
            event_query="техзадание Роману",
            start_iso="2099-08-11T13:20:00+03:00",
            timezone="Europe/Moscow",
        )

    monkeypatch.setattr(chat_router, "extract_intent", intent)
    response = logged_in.post(
        "/api/v1/chat/messages",
        json={"text": "Поменяй напоминание Роману на 13:20"},
    )

    assert response.status_code == 200
    assert "updated" in response.json()["message"]
    with SessionLocal() as db:
        reminder = db.scalar(
            select(Reminder).where(
                Reminder.title == "Отправить техзадание Роману в самолёт"
            )
        )
        assert reminder.status == "scheduled"
        assert reminder.attempts == 0
        assert reminder.due_at.isoformat().startswith("2099-08-11T10:20:00")


def test_task_search_is_flexible_but_ambiguous_matches_are_not_mutated(
    logged_in, monkeypatch
):
    with SessionLocal() as db:
        user = db.scalar(select(User))
        db.add_all(
            [
                LocalTask(user_id=user.id, title="Отправить отчёт Роману"),
                LocalTask(user_id=user.id, title="Позвонить Роману"),
            ]
        )
        db.commit()

    async def intent(*args, **kwargs):
        return Intent(intent="complete_task", event_query="Роману")

    monkeypatch.setattr(chat_router, "extract_intent", intent)
    response = logged_in.post(
        "/api/v1/chat/messages", json={"text": "Заверши задачу Роману"}
    )

    assert response.status_code == 200
    assert "several matches" in response.json()["message"]
    with SessionLocal() as db:
        assert all(row.status == "open" for row in db.scalars(select(LocalTask)).all())
