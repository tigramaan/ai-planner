import pytest
from sqlalchemy import select

from app import adapters
from app.config import get_settings
from app.database import SessionLocal
from app.models import User
from app.policy import create_pending_action
from app.routers import planner


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


@pytest.mark.anyio
async def test_standalone_teams_meeting_is_idempotent_and_verified(monkeypatch):
    calls = []

    async def request(method, url, token, **kwargs):
        calls.append((method, url, kwargs.get("json")))
        return {"id": "meeting/id", "joinWebUrl": "https://teams.example/join"}

    monkeypatch.setattr(adapters, "provider_request", request)
    result = await adapters.create_teams_online_meeting(
        "token",
        {
            "idempotency_key": "action-1",
            "start_iso": "2026-08-03T09:30:00+00:00",
            "end_iso": "2026-08-03T10:00:00+00:00",
            "title": "Meeting",
        },
    )
    assert [call[0] for call in calls] == ["POST", "GET"]
    assert calls[0][2]["externalId"] == "action-1"
    assert calls[1][1].endswith("meeting%2Fid")
    assert result["joinWebUrl"] == "https://teams.example/join"


@pytest.mark.anyio
async def test_zoom_meeting_is_created_and_verified(monkeypatch):
    calls = []

    async def request(method, url, token, **kwargs):
        calls.append((method, url, kwargs.get("json")))
        return {"id": 42, "join_url": "https://zoom.example/j/42"}

    monkeypatch.setattr(adapters, "provider_request", request)
    result = await adapters.create_zoom_meeting(
        "token",
        {
            "title": "Meeting",
            "start_iso": "2026-08-03T09:30:00+00:00",
            "end_iso": "2026-08-03T10:00:00+00:00",
            "timezone": "Europe/Moscow",
        },
    )
    assert [call[0] for call in calls] == ["POST", "GET"]
    assert calls[0][1].endswith("/users/me/meetings")
    assert calls[0][2]["duration"] == 30
    assert result["join_url"] == "https://zoom.example/j/42"


@pytest.mark.anyio
async def test_calendar_event_uses_configured_five_minute_reminder(monkeypatch):
    calls = []

    async def request(method, url, token, **kwargs):
        calls.append((method, kwargs.get("json")))
        return {"id": "event-1"}

    monkeypatch.setattr(adapters, "provider_request", request)
    await adapters.create_calendar_event(
        "google",
        "token",
        {
            "title": "Meeting",
            "start_iso": "2026-08-03T12:30:00+00:00",
            "end_iso": "2026-08-03T13:00:00+00:00",
            "timezone": "Europe/Moscow",
            "attendees": [],
            "conference": "none",
            "idempotency_key": "action-1",
            "reminder_minutes": 5,
        },
    )
    assert calls[0][1]["reminders"] == {
        "useDefault": False,
        "overrides": [{"method": "popup", "minutes": 5}],
    }


def test_confirm_creates_teams_link_inside_google_event(logged_in, monkeypatch):
    calls = []

    async def token(db, settings, user, provider):
        return f"{provider}-token"

    async def teams(token_value, payload):
        calls.append(("teams", token_value))
        return {"id": "teams-1", "joinWebUrl": "https://teams.example/join"}

    async def calendar(provider, token_value, payload):
        calls.append(("calendar", provider, token_value, payload.get("external_join_url")))
        return {"id": "google-1", "htmlLink": "https://calendar.example/event"}

    monkeypatch.setattr(planner, "valid_access_token", token)
    monkeypatch.setattr(planner, "create_teams_online_meeting", teams)
    monkeypatch.setattr(planner, "create_calendar_event", calendar)
    with SessionLocal() as db:
        user = db.scalar(select(User))
        action = create_pending_action(
            db,
            get_settings(),
            user,
            "create_meeting",
            "Google Calendar + Teams",
            {
                "provider": "google",
                "conference": "microsoft_teams",
                "title": "Meeting",
                "start_iso": "2026-08-03T09:30:00+00:00",
                "end_iso": "2026-08-03T10:00:00+00:00",
                "timezone": "Europe/Moscow",
                "attendees": ["guest@example.com"],
            },
        )
        db.commit()
        action_id = action.id
    response = logged_in.post(f"/api/v1/pending-actions/{action_id}/confirm")
    assert response.status_code == 200
    assert response.json()["result"]["link"] == "https://teams.example/join"
    assert calls == [
        ("teams", "microsoft-token"),
        ("calendar", "google", "google-token", "https://teams.example/join"),
    ]


def test_confirm_keeps_calendar_event_when_teams_rejects_request(logged_in, monkeypatch):
    async def token(db, settings, user, provider):
        return f"{provider}-token"

    async def teams(token_value, payload):
        raise adapters.ProviderError("Provider request failed (400)", 400)

    async def calendar(provider, token_value, payload):
        assert payload["conference"] == "none"
        return {"id": "google-1", "htmlLink": "https://calendar.example/event"}

    monkeypatch.setattr(planner, "valid_access_token", token)
    monkeypatch.setattr(planner, "create_teams_online_meeting", teams)
    monkeypatch.setattr(planner, "create_calendar_event", calendar)
    with SessionLocal() as db:
        user = db.scalar(select(User))
        action = create_pending_action(
            db,
            get_settings(),
            user,
            "create_meeting",
            "Google Calendar + Teams",
            {
                "provider": "google",
                "conference": "microsoft_teams",
                "title": "Meeting",
                "start_iso": "2026-08-03T09:30:00+00:00",
                "end_iso": "2026-08-03T10:00:00+00:00",
                "timezone": "Europe/Moscow",
                "attendees": ["guest@example.com"],
            },
        )
        db.commit()
        action_id = action.id
    response = logged_in.post(f"/api/v1/pending-actions/{action_id}/confirm")
    assert response.status_code == 200
    result = response.json()["result"]
    assert result["link"] == "https://calendar.example/event"
    assert result["warnings"] == ["Microsoft Teams meeting was not created"]


def test_confirm_uses_encrypted_teams_fallback_when_api_rejects(logged_in, monkeypatch):
    from app.conference_fallbacks import store_fallback_url

    async def token(db, settings, user, provider):
        return f"{provider}-token"

    async def teams(token_value, payload):
        raise adapters.ProviderError("Provider request failed (400)", 400)

    async def calendar(provider, token_value, payload):
        assert payload["external_join_url"] == "https://teams.microsoft.com/l/meetup-join/fallback"
        return {"id": "google-2", "htmlLink": "https://calendar.example/event-2"}

    monkeypatch.setattr(planner, "valid_access_token", token)
    monkeypatch.setattr(planner, "create_teams_online_meeting", teams)
    monkeypatch.setattr(planner, "create_calendar_event", calendar)
    with SessionLocal() as db:
        user = db.scalar(select(User))
        user.fallback_teams_url_encrypted = store_fallback_url(
            get_settings(),
            user,
            "microsoft_teams",
            "https://teams.microsoft.com/l/meetup-join/fallback",
        )
        action = create_pending_action(
            db,
            get_settings(),
            user,
            "create_meeting",
            "Google Calendar + Teams fallback",
            {
                "provider": "google",
                "conference": "microsoft_teams",
                "title": "Meeting",
                "start_iso": "2026-08-03T09:30:00+00:00",
                "end_iso": "2026-08-03T10:00:00+00:00",
                "timezone": "Europe/Moscow",
                "attendees": ["guest@example.com"],
            },
        )
        db.commit()
        action_id = action.id
    response = logged_in.post(f"/api/v1/pending-actions/{action_id}/confirm")
    assert response.status_code == 200
    result = response.json()["result"]
    assert result["link"] == "https://teams.microsoft.com/l/meetup-join/fallback"
    assert result["warnings"] == [
        "Microsoft Teams API failed; permanent fallback room used"
    ]
