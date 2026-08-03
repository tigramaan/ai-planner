import base64
from email import policy
from email.parser import BytesParser

import pytest

from app import adapters


@pytest.mark.anyio
async def test_gmail_message_is_composed_and_verified(monkeypatch):
    calls = []

    async def request(method, url, token, **kwargs):
        calls.append((method, url, kwargs))
        if method == "POST":
            raw = kwargs["json"]["raw"]
            decoded = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))
            message = BytesParser(policy=policy.default).parsebytes(decoded)
            assert message["To"] == "recipient@example.com"
            assert message["Subject"] == "Итоги проекта"
            assert "Добрый день" in message.get_content()
            return {"id": "gmail-message-id"}
        return {"id": "gmail-message-id", "threadId": "gmail-thread-id"}

    monkeypatch.setattr(adapters, "provider_request", request)
    result = await adapters.send_email(
        "google",
        "token",
        {
            "recipients": ["recipient@example.com"],
            "subject": "Итоги проекта",
            "body": "Добрый день! Отправляю итоги проекта.",
        },
    )

    assert result == {
        "id": "gmail-message-id",
        "thread_id": "gmail-thread-id",
        "status": "sent",
    }
    assert [call[0] for call in calls] == ["POST", "GET"]
