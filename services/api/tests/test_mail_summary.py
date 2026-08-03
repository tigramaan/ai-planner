import pytest

from app import mail_summary


@pytest.mark.anyio
async def test_google_summary_reports_subject_sender_and_attachments(monkeypatch):
    async def message(*args):
        return {"payload": {}}

    async def bundle(*args):
        return "Project total: 500", ["estimate.xlsx"], []

    async def summary(*args):
        return "Стоимость проекта — 500."

    monkeypatch.setattr(mail_summary, "gmail_message", message)
    monkeypatch.setattr(mail_summary, "email_text_bundle", bundle)
    monkeypatch.setattr(mail_summary, "summarize_email_content", summary)

    result = await mail_summary.summarize_google_email(
        "token",
        {"id": "message-1", "subject": "Смета", "from": "Виталий"},
        {"api_key": "key", "model": "model", "reasoning_effort": "low"},
        "ru",
    )

    assert result.startswith("Смета | Виталий")
    assert "Стоимость проекта — 500." in result
    assert "Вложения: estimate.xlsx" in result
