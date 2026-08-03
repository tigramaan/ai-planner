from app.action_summary import action_result_summary, action_summary
from app.agent import risk_for_intent
from app.routers.chat import decision
from app.schemas import Intent


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
    assert "03.08.2026, 11:25-11:55" in summary
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


def test_all_external_writes_require_confirmation():
    for name in (
        "create_meeting",
        "update_event",
        "cancel_event",
        "add_event_participants",
        "send_email",
    ):
        assert risk_for_intent(Intent(intent=name)) == "confirmation_required"


def test_completed_meeting_report_contains_details_and_both_links():
    result = action_result_summary(
        "create_meeting",
        {
            "title": "Встреча с Иваном Ивановичем",
            "start_iso": "2026-08-04T09:30:00+00:00",
            "end_iso": "2026-08-04T10:00:00+00:00",
            "timezone": "Europe/Moscow",
            "provider": "google",
            "attendees": ["ivan@example.com"],
        },
        {
            "htmlLink": "https://calendar.example/event",
            "onlineMeeting": {"joinUrl": "https://meet.example/room"},
        },
        [],
        "ru",
    )
    assert "Встреча создана: «Встреча с Иваном Ивановичем»" in result["report"]
    assert "04.08.2026, 12:30-13:00" in result["report"]
    assert "Участники: ivan@example.com" in result["report"]
    assert result["calendar_link"] == "https://calendar.example/event"
    assert result["join_link"] == "https://meet.example/room"
