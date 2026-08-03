import json

import pytest
from cryptography.exceptions import InvalidTag
from sqlalchemy import select

from app.config import get_settings
from app.database import SessionLocal
from app.models import Integration, User
from app.oauth import consume_state, create_state, resolve_scopes
from app.security import decrypt_json, encrypt_json, redact


def test_encryption_roundtrip_and_context_binding():
    settings = get_settings()
    encoded = encrypt_json(settings, {"api_key": "secret"}, "provider:one")
    assert "secret" not in encoded
    assert decrypt_json(settings, encoded, "provider:one") == {"api_key": "secret"}
    with pytest.raises(InvalidTag):
        decrypt_json(settings, encoded, "provider:two")


def test_openai_secret_never_returned(logged_in):
    response = logged_in.post(
        "/api/v1/integrations/openai",
        json={
            "api_key": "sk-this-is-a-test-only-key",
            "model": "gpt-test",
            "transcription_model": "whisper-1",
        },
    )
    assert response.status_code == 200
    assert "api_key" not in json.dumps(response.json())
    with SessionLocal() as db:
        integration = db.scalar(select(Integration).where(Integration.provider == "openai"))
        assert "sk-this" not in integration.secret.encrypted_payload


def test_oauth_state_is_single_use(logged_in):
    with SessionLocal() as db:
        user = db.scalar(select(User))
        raw = create_state(db, user, "google", ["openid"])
        assert consume_state(db, raw, "google").used_at
        with pytest.raises(ValueError):
            consume_state(db, raw, "google")


def test_scope_groups_are_allowlisted():
    assert "Calendars.ReadWrite" in resolve_scopes("microsoft", ["calendar"])
    assert resolve_scopes("zoom", ["meeting"]) == ["meeting:write:meeting"]
    with pytest.raises(ValueError):
        resolve_scopes("google", ["drive.everything"])


def test_redaction_is_recursive():
    value = redact({"api_key": "x", "nested": [{"refresh_token": "y", "safe": 1}]})
    assert value == {
        "api_key": "[redacted]",
        "nested": [{"refresh_token": "[redacted]", "safe": 1}],
    }


def test_untrusted_host_is_rejected(client):
    response = client.get("/health/live", headers={"Host": "attacker.example"})
    assert response.status_code == 400
