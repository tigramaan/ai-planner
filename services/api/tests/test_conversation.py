import json

import pytest

from app import agent


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
