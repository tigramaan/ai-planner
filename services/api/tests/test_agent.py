from app.agent import pending_payload
from app.schemas import Intent


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
    assert payload["conference"] == "microsoft_teams"


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
        )
    )
    assert payload["provider"] == "google"
    assert payload["conference"] == "microsoft_teams"
