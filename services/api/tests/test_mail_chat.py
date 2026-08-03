import pytest

from app import mail_chat
from app.schemas import Intent


@pytest.mark.anyio
async def test_triage_search_fetches_twenty_and_uses_classifier(monkeypatch):
    captured = {}

    async def token(*args):
        return "token"

    async def search(provider, access_token, query, limit):
        captured.update(provider=provider, token=access_token, query=query, limit=limit)
        return [{"subject": "Budget", "from": "manager@example.com", "snippet": "Review"}]

    async def triage(rows, config, locale):
        captured.update(rows=rows, config=config, locale=locale)
        return "Needs attention"

    monkeypatch.setattr(mail_chat, "mail_access_granted", lambda *args: True)
    monkeypatch.setattr(mail_chat, "valid_access_token", token)
    monkeypatch.setattr(mail_chat, "search_email", search)
    monkeypatch.setattr(mail_chat, "triage_mail_answer", triage)
    user = type("User", (), {"default_mail": "google", "timezone": "Europe/Moscow"})()
    result = await mail_chat.handle_mail_search(
        object(),
        object(),
        user,
        Intent(intent="search_email", provider="google", mail_mode="triage"),
        "Выбери важные письма за сегодня, а рассылки убери",
        {"api_key": "key", "model": "model", "reasoning_effort": "low"},
        "ru",
    )

    assert result == "Needs attention"
    assert captured["limit"] == 20
    assert "after:" in captured["query"]
