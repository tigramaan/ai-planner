from app.action_summary import action_summary
from app.routers.chat import decision


def test_meeting_summary_explains_every_external_effect():
    summary = action_summary(
        "create_meeting",
        {
            "title": "Встреча с Анастасией",
            "start_iso": "2026-08-03T08:25:00+00:00",
            "end_iso": "2026-08-03T08:55:00+00:00",
            "timezone": "Europe/Moscow",
            "provider": "microsoft",
            "conference": "microsoft_teams",
            "attendees": ["anastasia@example.com"],
        },
        "ru",
    )
    assert "03.08.2026, 11:25–11:55" in summary
    assert "Europe/Moscow" in summary
    assert "anastasia@example.com" in summary
    assert "Календарь: Microsoft" in summary
    assert "Видеосвязь: Microsoft Teams" in summary
    assert "Напоминание: за 5 мин." in summary
    assert "календарные приглашения" in summary


def test_only_unambiguous_short_replies_are_decisions():
    assert decision("Давай!") == "confirm"
    assert decision("Подтверждаю") == "confirm"
    assert decision("Нет") == "cancel"
    assert decision("Давай перенесём на 16:00") is None


def test_summary_distinguishes_google_calendar_from_teams_video():
    summary = action_summary(
        "create_meeting",
        {
            "title": "Встреча",
            "start_iso": "2026-08-03T09:30:00+00:00",
            "end_iso": "2026-08-03T10:00:00+00:00",
            "timezone": "Europe/Moscow",
            "provider": "google",
            "conference": "microsoft_teams",
        },
        "ru",
    )
    assert "Календарь: Google" in summary
    assert "Видеосвязь: Microsoft Teams" in summary
