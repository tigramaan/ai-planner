from sqlalchemy import select

from app.config import get_settings
from app.database import SessionLocal
from app.models import PendingAction
from app.routers import chat as chat_router
from app.schemas import Intent
from app.security import decrypt_json


def test_meeting_follow_up_replaces_default_reminder_with_two_hours(logged_in, monkeypatch):
    responses = iter(
        [
            Intent(
                intent="create_meeting",
                title="Компания wp group",
                start_iso="2026-08-18T16:00:00+03:00",
                timezone="Europe/Moscow",
            ),
            Intent(
                intent="create_meeting",
                title="Компания wp group",
                start_iso="2026-08-18T16:00:00+03:00",
                timezone="Europe/Moscow",
                reminder_minutes=120,
            ),
        ]
    )

    async def intent(*args, **kwargs):
        return next(responses)

    monkeypatch.setattr(chat_router, "extract_intent", intent)
    first = logged_in.post("/api/v1/chat/messages", json={"text": "Встреча завтра в 16:00"})
    second = logged_in.post("/api/v1/chat/messages", json={"text": "Напоминание за 2 часа"})
    assert first.status_code == second.status_code == 200
    assert "Reminder: 120 min before." in second.json()["message"]
    with SessionLocal() as db:
        action = db.scalar(
            select(PendingAction)
            .where(PendingAction.cancelled_at.is_(None))
            .order_by(PendingAction.expires_at.desc())
        )
        payload = decrypt_json(
            get_settings(), action.payload_encrypted, f"pending:{action.id}:{action.payload_hash}"
        )
        assert payload["reminder_minutes"] == 120


def test_client_join_link_is_preserved_in_pending_meeting(logged_in, monkeypatch):
    async def intent(*args, **kwargs):
        return Intent(
            intent="create_meeting",
            title="Онлайн-консультация",
            start_iso="2026-08-18T10:00:00+03:00",
            timezone="Europe/Moscow",
        )

    monkeypatch.setattr(chat_router, "extract_intent", intent)
    response = logged_in.post(
        "/api/v1/chat/messages",
        json={
            "text": (
                "Создай мероприятие по приглашению: онлайн-консультация завтра в 10:00. "
                "Откройте ссылку https://diagnostics.ktalk.ru/oqoq1ob080bm"
            )
        },
    )
    assert response.status_code == 200
    assert "client link: https://diagnostics.ktalk.ru/oqoq1ob080bm" in response.json()["message"]
    with SessionLocal() as db:
        action = db.scalar(select(PendingAction).where(PendingAction.cancelled_at.is_(None)))
        payload = decrypt_json(
            get_settings(), action.payload_encrypted, f"pending:{action.id}:{action.payload_hash}"
        )
        assert payload["external_join_url"] == "https://diagnostics.ktalk.ru/oqoq1ob080bm"
        assert payload["conference"] == "none"
