import pytest

from app import adapters


@pytest.mark.anyio
async def test_google_contact_search_normalizes_people_response(monkeypatch):
    async def request(method, url, token, **kwargs):
        assert url.endswith("people/me/connections")
        assert kwargs["params"]["personFields"] == "names,emailAddresses"
        return {
            "connections": [
                {
                    "names": [{"displayName": "Анастасия Сорокина"}],
                    "emailAddresses": [{"value": "anastasia@example.com"}],
                }
            ]
        }

    monkeypatch.setattr(adapters, "provider_request", request)
    assert await adapters.search_contacts("google", "token", "Анастасия") == [
        {"name": "Анастасия Сорокина", "email": "anastasia@example.com"}
    ]


@pytest.mark.anyio
async def test_microsoft_contact_search_normalizes_graph_response(monkeypatch):
    async def request(method, url, token, **kwargs):
        assert url.endswith("/me/contacts")
        return {
            "value": [
                {
                    "displayName": "Anastasia Sorokina",
                    "emailAddresses": [{"address": "anastasia@example.com"}],
                }
            ]
        }

    monkeypatch.setattr(adapters, "provider_request", request)
    assert await adapters.search_contacts("microsoft", "token", "Anastasia") == [
        {"name": "Anastasia Sorokina", "email": "anastasia@example.com"}
    ]
