import json

import pytest

from app import agent
from app.agent import pending_payload
from app.conference_intent import explicit_conference_provider
from app.schemas import Intent


@pytest.mark.anyio
async def test_reminder_time_in_event_field_is_normalized(monkeypatch):
    class Responses:
        async def create(self, **kwargs):
            return type(
                "Response",
                (),
                {
                    "output_text": json.dumps(
                        {
                            "intent": "create_reminder",
                            "title": "Перезвонить Татьяне в Новоспасский",
                            "event_query": None,
                            "event_start_iso": "2026-08-13T12:37:19+03:00",
                            "start_iso": None,
                            "timezone": "Europe/Moscow",
                            "duration_minutes": None,
                            "priority": None,
                            "participants": [],
                            "provider": None,
                            "mail_mode": "search",
                            "mail_limit": None,
                            "conference_provider": None,
                            "conference_requested": False,
                            "body": None,
                            "requires_senior": False,
                            "route_reason": None,
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
        "key",
        "model",
        "поставь напоминание перезвонить Татьяне в Новоспасский через час",
        "ru",
        "Europe/Moscow",
    )

    assert intent.start_iso == "2026-08-13T12:37:19+03:00"
    assert intent.event_start_iso is None


def test_meeting_intent_becomes_calendar_payload():
    payload = pending_payload(
        Intent(
            intent="create_meeting",
            title="Семейный звонок",
            start_iso="2026-08-03T15:00:00+07:00",
            timezone="Asia/Jakarta",
            duration_minutes=45,
            participants=["family@example.com"],
            provider="microsoft",
        )
    )
    assert payload["start_iso"] == "2026-08-03T08:00:00+00:00"
    assert payload["end_iso"] == "2026-08-03T08:45:00+00:00"
    assert payload["attendees"] == ["family@example.com"]
    assert payload["conference"] == "none"


def test_meeting_payload_rejects_time_without_offset():
    intent = Intent(
        intent="create_meeting",
        title="Звонок",
        start_iso="2026-08-03T15:00:00",
        timezone="Asia/Jakarta",
    )
    try:
        pending_payload(intent)
    except ValueError as error:
        assert "UTC offset" in str(error)
    else:
        raise AssertionError("naive meeting time was accepted")


def test_email_intent_becomes_confirmable_provider_payload():
    payload = pending_payload(
        Intent(
            intent="send_email",
            title="Подтверждение встречи",
            body="Подтверждаю встречу завтра.",
            participants=["family@example.com"],
            provider="google",
        )
    )
    assert payload["subject"] == "Подтверждение встречи"
    assert payload["body"] == "Подтверждаю встречу завтра."
    assert payload["recipients"] == ["family@example.com"]
    assert payload["provider"] == "google"


def test_meeting_uses_moscow_time_with_explicit_offset():
    payload = pending_payload(
        Intent(
            intent="create_meeting",
            title="Встреча с Анастасией Сорокиной",
            start_iso="2026-08-03T11:25:00+03:00",
            timezone="Europe/Moscow",
            participants=["anastasia@example.com"],
            provider="microsoft",
        )
    )
    assert payload["start_iso"] == "2026-08-03T08:25:00+00:00"
    assert payload["timezone"] == "Europe/Moscow"


def test_google_calendar_can_use_teams_conference():
    payload = pending_payload(
        Intent(
            intent="create_meeting",
            title="Гибридная встреча",
            start_iso="2026-08-03T12:30:00+03:00",
            timezone="Europe/Moscow",
            participants=["guest@example.com"],
            provider="google",
            conference_provider="microsoft",
            conference_requested=True,
        )
    )
    assert payload["provider"] == "google"
    assert payload["conference"] == "microsoft_teams"


def test_explicit_telemost_replaces_teams_from_old_context():
    assert explicit_conference_provider("Время 15:30 и встреча в Телемосте") == "yandex"
    assert explicit_conference_provider("Сделай встречу в Яндексе") == "yandex"
    assert explicit_conference_provider("Добавь встречу в Яндекс Календарь") is None
