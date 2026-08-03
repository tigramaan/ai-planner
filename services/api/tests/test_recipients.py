import pytest

from app import recipients
from app.config import Settings
from app.models import User


def test_candidate_addresses_prefers_exact_contact_name():
    result = recipients.candidate_addresses(
        "Анастасия Сорокина",
        [
            {"name": "Анастасия Сорокина", "email": "anastasia@example.com"},
            {"name": "Анастасия", "email": "other@example.com"},
        ],
        [],
    )
    assert result == ["anastasia@example.com"]


@pytest.mark.anyio
async def test_resolver_uses_contacts_when_mail_scope_is_missing(monkeypatch):
    async def token(db, settings, user, provider):
        if provider != "google":
            raise LookupError
        return "token"

    async def contacts(provider, token, query):
        return [{"name": "Anastasia Sorokina", "email": "Anastasia@Example.com"}]

    async def mail(provider, token, query):
        raise recipients.ProviderError("mail scope missing")

    monkeypatch.setattr(recipients, "valid_access_token", token)
    monkeypatch.setattr(recipients, "search_contacts", contacts)
    monkeypatch.setattr(recipients, "search_email", mail)
    result = await recipients.resolve_recipients(
        None,
        Settings(),
        User(email="owner@example.com", password_hash="hash"),
        ["Anastasia Sorokina"],
        "google",
    )
    assert result.recipients == ["anastasia@example.com"]
    assert not result.unresolved


@pytest.mark.anyio
async def test_resolver_requires_choice_for_multiple_addresses(monkeypatch):
    async def token(db, settings, user, provider):
        if provider != "google":
            raise LookupError
        return "token"

    async def contacts(provider, token, query):
        return [
            {"name": query, "email": "one@example.com"},
            {"name": query, "email": "two@example.com"},
        ]

    async def mail(provider, token, query):
        return []

    monkeypatch.setattr(recipients, "valid_access_token", token)
    monkeypatch.setattr(recipients, "search_contacts", contacts)
    monkeypatch.setattr(recipients, "search_email", mail)
    result = await recipients.resolve_recipients(
        None,
        Settings(),
        User(email="owner@example.com", password_hash="hash"),
        ["Anastasia Sorokina"],
        "google",
    )
    assert result.ambiguous == {
        "Anastasia Sorokina": ["one@example.com", "two@example.com"]
    }
