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


@pytest.mark.anyio
async def test_triage_answer_only_lists_useful_messages(monkeypatch):
    async def classify(*args):
        return [
            {
                "index": 0,
                "category": "ignore",
                "reason": "Промо",
                "suggested_action": "",
            },
            {
                "index": 1,
                "category": "action",
                "reason": "Запрошено согласование сметы.",
                "suggested_action": "Проверить сумму и ответить.",
            },
        ]

    monkeypatch.setattr(mail_summary, "triage_email_rows", classify)
    result = await mail_summary.triage_mail_answer(
        [
            {"subject": "Скидки недели", "from": "promo@example.com"},
            {"subject": "Смета на согласование", "from": "manager@example.com"},
        ],
        {"api_key": "key", "model": "model", "reasoning_effort": "low"},
        "ru",
    )

    assert "Смета на согласование" in result
    assert "Проверить сумму и ответить" in result
    assert "Скидки недели" not in result
    assert "Отсеяно как рассылки, промо или несущественное: 1" in result
