import base64

import pytest

from app.mail_documents import email_text_bundle


def encoded(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode()).decode().rstrip("=")


@pytest.mark.anyio
async def test_email_bundle_extracts_body_and_text_attachment():
    message = {
        "payload": {
            "mimeType": "multipart/mixed",
            "parts": [
                {"mimeType": "text/html", "body": {"data": encoded("<b>Цена:</b> 100 ₽")}},
                {
                    "mimeType": "text/plain",
                    "filename": "estimate.txt",
                    "body": {"attachmentId": "attachment-1"},
                },
            ],
        }
    }

    async def loader(attachment_id: str) -> bytes:
        assert attachment_id == "attachment-1"
        return "Итого: 250 ₽".encode()

    content, attachments, warnings = await email_text_bundle(message, loader)

    assert "Цена: 100 ₽" in content
    assert "Итого: 250 ₽" in content
    assert attachments == ["estimate.txt"]
    assert warnings == []
