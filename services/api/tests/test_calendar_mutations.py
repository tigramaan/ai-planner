import pytest

from app import adapters


@pytest.mark.anyio
async def test_update_event_is_read_after_write(monkeypatch):
    calls = []

    async def request(method, url, token, **kwargs):
        calls.append((method, kwargs))
        return {"id": "event-1", "subject": "Updated"}

    monkeypatch.setattr(adapters, "provider_request", request)
    result = await adapters.update_calendar_event(
        "microsoft",
        "token",
        {
            "event_id": "event-1",
            "start_iso": "2026-08-03T12:20:00+00:00",
            "end_iso": "2026-08-03T12:50:00+00:00",
            "timezone": "Europe/Moscow",
        },
    )
    assert [method for method, _ in calls] == ["PATCH", "GET"]
    assert calls[0][1]["json"]["start"] == {
        "dateTime": "2026-08-03T12:20:00",
        "timeZone": "UTC",
    }
    assert result["id"] == "event-1"


@pytest.mark.anyio
async def test_cancel_event_verifies_provider_404(monkeypatch):
    calls = []

    async def request(method, url, token, **kwargs):
        calls.append(method)
        if method == "GET":
            raise adapters.ProviderError("not found", 404)
        return {}

    monkeypatch.setattr(adapters, "provider_request", request)
    result = await adapters.cancel_calendar_event("google", "token", "event-1")
    assert calls == ["DELETE", "GET"]
    assert result == {"id": "event-1", "status": "cancelled"}
