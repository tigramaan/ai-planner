from datetime import datetime
from zoneinfo import ZoneInfo

from app.mail_queries import provider_mail_query
from app.schemas import Intent


def test_google_unread_today_uses_native_operators():
    intent = Intent(
        intent="search_email",
        event_query="непрочитанные письма за сегодня",
        provider="google",
    )

    query = provider_mail_query(
        "google",
        intent,
        "Покажи непрочитанные письма за сегодня",
        "Europe/Moscow",
        datetime(2026, 8, 3, 15, 0, tzinfo=ZoneInfo("Europe/Moscow")),
    )

    assert query == "is:unread after:2026/08/03 before:2026/08/04"


def test_google_sender_and_attachment_use_native_operators():
    intent = Intent(
        intent="search_email",
        event_query="Письма от Виталия Лопатина с прикреплёнными документами",
        participants=["Виталий Лопатин"],
        provider="google",
    )

    query = provider_mail_query(
        "google",
        intent,
        "Есть ли письма от Виталия Лопатина? Там должны быть документы приложены",
        "Europe/Moscow",
    )

    assert query == 'has:attachment from:"Виталий Лопатин"'


def test_microsoft_keeps_natural_search_text():
    intent = Intent(intent="search_email", event_query="quarterly report", provider="microsoft")

    assert (
        provider_mail_query("microsoft", intent, "Find the report", "Europe/Moscow")
        == "quarterly report"
    )
