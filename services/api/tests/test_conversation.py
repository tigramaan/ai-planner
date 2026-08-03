import json

import pytest
from sqlalchemy import select

from app import agent
from app.database import SessionLocal
from app.models import PendingAction
from app.routers import chat as chat_router
from app.schemas import Intent


@pytest.mark.anyio
async def test_intent_extraction_includes_bounded_conversation_context(monkeypatch):
    captured = {}

    class Responses:
        async def create(self, **kwargs):
            captured.update(kwargs)
            return type(
                "Response",
                (),
                {
                    "output_text": json.dumps(
                        {
                            "intent": "create_meeting",
                            "title": "Teams meeting",
                            "start_iso": "2026-08-03T11:25:00+03:00",
                            "timezone": "Europe/Moscow",
                            "duration_minutes": 30,
                            "participants": ["sorokina@example.com"],
                            "provider": "microsoft",
                            "body": None,
                            "requires_clarification": False,
                            "clarification_question": None,
                        }
                    )
                },
            )()

    class Client:
        def __init__(self, **kwargs):
            self.responses = Responses()

    monkeypatch.setattr(agent, "AsyncOpenAI", Client)
    intent = await agent.extract_intent(
        "test-key",
        "test-model",
        "Москва, sorokina@example.com",
        "ru",
        "Europe/Moscow",
        [
            {"role": "user", "text": "Поставь встречу в Teams сегодня в 11:25"},
            {"role": "assistant", "text": "Укажите email и таймзону"},
        ],
    )
    sent = json.loads(captured["input"])
    assert sent["conversation_history"][0]["role"] == "user"
    assert sent["current_user_message"] == "Москва, sorokina@example.com"
    assert intent.intent == "create_meeting"
    assert intent.participants == ["sorokina@example.com"]


def test_correction_replaces_pending_draft(logged_in, monkeypatch):
    async def intent(*args, **kwargs):
        text = args[2]
        hour = 16 if "16:00" in text else 15
        return Intent(
            intent="create_meeting",
            title="Встреча с Анастасией",
            start_iso=f"2026-08-04T{hour:02d}:00:00+03:00",
            timezone="Europe/Moscow",
            participants=["anastasia@example.com"],
            provider="microsoft",
        )

    async def recipients(*args, **kwargs):
        return type("Resolution", (), {"recipients": args[3], "ambiguous": {}, "unresolved": []})()

    monkeypatch.setattr(chat_router, "extract_intent", intent)
    monkeypatch.setattr(chat_router, "resolve_recipients", recipients)
    first = logged_in.post("/api/v1/chat/messages", json={"text": "Встреча завтра в 15:00"})
    second = logged_in.post("/api/v1/chat/messages", json={"text": "Нет, перенеси на 16:00"})
    assert first.status_code == second.status_code == 200
    assert "16:00" in second.json()["message"]
    with SessionLocal() as db:
        rows = db.scalars(select(PendingAction).order_by(PendingAction.expires_at)).all()
        assert len(rows) == 2
        assert rows[0].cancelled_at is not None
        assert rows[1].cancelled_at is None
