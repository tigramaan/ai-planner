from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from .adapters import list_calendar_events
from .config import Settings
from .integrations import valid_access_token
from .models import User
from .schemas import Intent


class EventNotFound(LookupError):
    pass


class EventAmbiguous(ValueError):
    def __init__(self, choices: list[str]):
        super().__init__("Calendar event is ambiguous")
        self.choices = choices


@dataclass
class CalendarEvent:
    id: str
    title: str
    start: datetime
    end: datetime
    attendees: list[str]


def parse_provider_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def normalize_event(provider: str, row: dict[str, Any]) -> CalendarEvent | None:
    if provider == "google":
        start_value = (row.get("start") or {}).get("dateTime")
        end_value = (row.get("end") or {}).get("dateTime")
        attendees = [item.get("email", "") for item in row.get("attendees", [])]
        title = row.get("summary", "")
    else:
        start_value = (row.get("start") or {}).get("dateTime")
        end_value = (row.get("end") or {}).get("dateTime")
        attendees = [
            (item.get("emailAddress") or {}).get("address", "")
            for item in row.get("attendees", [])
        ]
        title = row.get("subject", "")
    if not row.get("id") or not start_value or not end_value:
        return None
    return CalendarEvent(
        id=row["id"],
        title=title,
        start=parse_provider_time(start_value),
        end=parse_provider_time(end_value),
        attendees=[email.casefold() for email in attendees if email],
    )


async def prepare_calendar_action(
    db: Session, settings: Settings, user: User, intent: Intent
) -> tuple[dict[str, Any], str]:
    provider = intent.provider if intent.provider in {"google", "microsoft"} else "google"
    token = await valid_access_token(db, settings, user, provider)
    anchor = datetime.fromisoformat(intent.event_start_iso) if intent.event_start_iso else None
    if anchor and anchor.tzinfo is None:
        raise ValueError("Existing event time requires UTC offset")
    now = datetime.now(UTC)
    window_start = anchor.astimezone(UTC) - timedelta(hours=12) if anchor else now - timedelta(days=1)
    window_end = anchor.astimezone(UTC) + timedelta(hours=12) if anchor else now + timedelta(days=90)
    rows = await list_calendar_events(provider, token, window_start, window_end)
    events = [event for row in rows if (event := normalize_event(provider, row))]
    query = (intent.event_query or intent.title or "").casefold().strip()
    if query:
        title_matches = [event for event in events if query in event.title.casefold()]
        if title_matches or not anchor:
            events = title_matches
    if anchor:
        events = [event for event in events if abs((event.start - anchor).total_seconds()) <= 900]
    if not events:
        raise EventNotFound("Calendar event not found")
    if len(events) > 1:
        raise EventAmbiguous(
            [f"{event.title} ({event.start.isoformat()})" for event in events[:5]]
        )
    event = events[0]
    payload: dict[str, Any] = {
        "schema_version": 1,
        "provider": provider,
        "event_id": event.id,
        "event_title": event.title,
        "original_start_iso": event.start.astimezone(UTC).isoformat(),
        "timezone": intent.timezone or user.timezone,
    }
    if intent.intent == "update_event":
        if not intent.start_iso:
            raise ValueError("New event time is required")
        new_start = datetime.fromisoformat(intent.start_iso)
        if new_start.tzinfo is None:
            raise ValueError("New event time requires UTC offset")
        duration = event.end - event.start
        payload.update(
            {
                "start_iso": new_start.astimezone(UTC).isoformat(),
                "end_iso": (new_start + duration).astimezone(UTC).isoformat(),
                "timezone": intent.timezone or user.timezone,
            }
        )
        summary = f"{event.title}: {event.start.isoformat()} -> {new_start.isoformat()}"
    elif intent.intent == "add_event_participants":
        if not intent.participants:
            raise ValueError("At least one participant is required")
        payload["attendees"] = list(dict.fromkeys([*event.attendees, *intent.participants]))
        payload["added_attendees"] = intent.participants
        summary = f"{event.title}: add {', '.join(intent.participants)}"
    else:
        summary = f"Cancel {event.title} ({event.start.isoformat()})"
    return payload, summary
