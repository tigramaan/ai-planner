import pytest

from app import calendar_actions
from app.config import Settings
from app.models import User
from app.schemas import Intent


def microsoft_event(event_id="event-1", title="Weekly sync", hour=12):
    return {
        "id": event_id,
        "subject": title,
        "start": {"dateTime": f"2026-08-03T{hour:02d}:30:00+03:00"},
        "end": {"dateTime": f"2026-08-03T{hour + 1:02d}:00:00+03:00"},
        "attendees": [
            {"emailAddress": {"address": "existing@example.com"}, "type": "required"}
        ],
    }


@pytest.fixture
def owner():
    return User(email="owner@example.com", password_hash="hash", timezone="Europe/Moscow")


@pytest.mark.anyio
async def test_prepare_reschedule_preserves_duration(monkeypatch, owner):
    async def token(*args):
        return "token"

    async def events(*args):
        return [microsoft_event()]

    monkeypatch.setattr(calendar_actions, "valid_access_token", token)
    monkeypatch.setattr(calendar_actions, "list_calendar_events", events)
    payload, summary = await calendar_actions.prepare_calendar_action(
        None,
        Settings(),
        owner,
        Intent(
            intent="update_event",
            event_query="meeting in Teams",
            event_start_iso="2026-08-03T12:30:00+03:00",
            start_iso="2026-08-03T15:20:00+03:00",
            timezone="Europe/Moscow",
            provider="microsoft",
        ),
    )
    assert payload["event_id"] == "event-1"
    assert payload["start_iso"] == "2026-08-03T12:20:00+00:00"
    assert payload["end_iso"] == "2026-08-03T12:50:00+00:00"
    assert "15:20" in summary


@pytest.mark.anyio
async def test_prepare_adds_participant_without_removing_existing(monkeypatch, owner):
    async def token(*args):
        return "token"

    async def events(*args):
        return [microsoft_event()]

    monkeypatch.setattr(calendar_actions, "valid_access_token", token)
    monkeypatch.setattr(calendar_actions, "list_calendar_events", events)
    payload, _ = await calendar_actions.prepare_calendar_action(
        None,
        Settings(),
        owner,
        Intent(
            intent="add_event_participants",
            event_query="Weekly sync",
            event_start_iso="2026-08-03T12:30:00+03:00",
            participants=["new@example.com"],
            provider="microsoft",
        ),
    )
    assert payload["attendees"] == ["existing@example.com", "new@example.com"]


@pytest.mark.anyio
async def test_prepare_requires_disambiguation(monkeypatch, owner):
    async def token(*args):
        return "token"

    async def events(*args):
        return [microsoft_event("one"), microsoft_event("two")]

    monkeypatch.setattr(calendar_actions, "valid_access_token", token)
    monkeypatch.setattr(calendar_actions, "list_calendar_events", events)
    with pytest.raises(calendar_actions.EventAmbiguous) as error:
        await calendar_actions.prepare_calendar_action(
            None,
            Settings(),
            owner,
            Intent(intent="cancel_event", event_query="Weekly sync", provider="microsoft"),
        )
    assert len(error.value.choices) == 2
