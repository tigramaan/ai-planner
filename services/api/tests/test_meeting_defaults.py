from sqlalchemy import select

from app.config import get_settings
from app.database import SessionLocal
from app.models import PendingAction
from app.routers import chat as chat_router
from app.schemas import Intent
from app.security import decrypt_json


def _misplaced_start(duration: int | None, clarification: bool = False) -> Intent:
    return Intent(
        intent="create_meeting",
        title="школа «Самолёт»",
        event_start_iso="2026-08-27T11:00:00+03:00",
        timezone="Europe/Moscow",
        duration_minutes=duration,
        reminder_minutes=120,
        requires_clarification=clarification,
        clarification_question="На сколько минут запланировать мероприятие?" if clarification else None,
    )


def test_meeting_without_duration_defaults_to_one_hour(logged_in, monkeypatch):
    async def intent(*args, **kwargs):
        return _misplaced_start(None, clarification=True)

    monkeypatch.setattr(chat_router, "extract_intent", intent)
    response = logged_in.post(
        "/api/v1/chat/messages",
        json={"text": "Создай школу Самолёт в четверг в 11, напомни за два часа"},
    )
    assert response.status_code == 200
    assert "11:00-12:00" in response.json()["message"]
    assert "Reminder: 120 min before." in response.json()["message"]


def test_explicit_180_minutes_replaces_default_duration(logged_in, monkeypatch):
    responses = iter([_misplaced_start(None, clarification=True), _misplaced_start(180)])

    async def intent(*args, **kwargs):
        return next(responses)

    monkeypatch.setattr(chat_router, "extract_intent", intent)
    logged_in.post("/api/v1/chat/messages", json={"text": "Создай мероприятие в четверг в 11"})
    response = logged_in.post("/api/v1/chat/messages", json={"text": "180 минут"})
    assert response.status_code == 200
    assert "11:00-14:00" in response.json()["message"]
    with SessionLocal() as db:
        action = db.scalar(
            select(PendingAction)
            .where(PendingAction.cancelled_at.is_(None))
            .order_by(PendingAction.expires_at.desc())
        )
        payload = decrypt_json(
            get_settings(), action.payload_encrypted, f"pending:{action.id}:{action.payload_hash}"
        )
        assert payload["duration_minutes"] == 180
        assert payload["end_iso"] == "2026-08-27T11:00:00+00:00"
