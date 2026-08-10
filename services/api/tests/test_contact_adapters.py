import pytest

from app import adapters


@pytest.mark.anyio
async def test_google_contact_search_normalizes_people_response(monkeypatch):
    calls = 0

    async def request(method, url, token, **kwargs):
        nonlocal calls
        calls += 1
        assert url.endswith("people/me/connections")
        assert kwargs["params"]["personFields"] == "names,emailAddresses"
        if calls == 1:
            return {
                "connections": [{"names": [{"displayName": "Другой человек"}]}],
                "nextPageToken": "page-2",
            }
        assert kwargs["params"]["pageToken"] == "page-2"
        return {
            "connections": [
                {
                    "names": [{"displayName": "Сорокина Анастасия"}],
                    "emailAddresses": [{"value": "anastasia@example.com"}],
                }
            ]
        }

    monkeypatch.setattr(adapters, "provider_request", request)
    assert await adapters.search_contacts("google", "token", "Anastasia Sorokina") == [
        {"name": "Сорокина Анастасия", "email": "anastasia@example.com"}
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
