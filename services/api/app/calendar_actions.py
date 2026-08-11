from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from .adapters import list_calendar_events
from .config import Settings
from .entity_matching import text_relevance
from .integrations import valid_access_token
from .models import User
from .schemas import Intent


class EventNotFound(LookupError):
    def __init__(self, choices: list[str] | None = None):
        super().__init__("Calendar event not found")
        self.choices = choices or []


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
    attendee_names: list[str]


def event_relevance(event: CalendarEvent, query: str) -> float:
    searchable = " ".join([event.title, *event.attendees, *event.attendee_names])
    return text_relevance(searchable, query)


def display_choice(event: CalendarEvent, timezone: str) -> str:
    local = event.start.astimezone(ZoneInfo(timezone))
    return f"{event.title} ({local.strftime('%d.%m.%Y, %H:%M')})"


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
        attendee_names = [item.get("displayName", "") for item in row.get("attendees", [])]
        title = row.get("summary", "")
    else:
        start_value = (row.get("start") or {}).get("dateTime")
        end_value = (row.get("end") or {}).get("dateTime")
        attendees = [
            (item.get("emailAddress") or {}).get("address", "")
            for item in row.get("attendees", [])
        ]
        attendee_names = [
            (item.get("emailAddress") or {}).get("name", "")
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
        attendee_names=[name for name in attendee_names if name],
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
    window_start = min(now - timedelta(days=7), anchor.astimezone(UTC) - timedelta(days=1)) if anchor else now - timedelta(days=7)
    window_end = max(now + timedelta(days=90), anchor.astimezone(UTC) + timedelta(days=1)) if anchor else now + timedelta(days=90)
    rows = await list_calendar_events(provider, token, window_start, window_end)
    events = [event for row in rows if (event := normalize_event(provider, row))]
    query = (intent.event_query or intent.title or "").casefold().strip()
    ranked = [(event, event_relevance(event, query)) for event in events]
    fuzzy = [(event, score) for event, score in ranked if score >= 0.58]
    if fuzzy:
        ranked = fuzzy
    elif query and not anchor:
        choices = [display_choice(event, user.timezone) for event in events[:5]]
        raise EventNotFound(choices)
    if anchor:
        anchor_utc = anchor.astimezone(UTC)
        ranked.sort(
            key=lambda item: (
                -item[1],
                item[0].start.astimezone(ZoneInfo(user.timezone)).date()
                != anchor.astimezone(ZoneInfo(user.timezone)).date(),
                abs((item[0].start - anchor_utc).total_seconds()),
            )
        )
    else:
        ranked.sort(key=lambda item: (-item[1], item[0].start))
    events = [event for event, _ in ranked]
    if not events:
        raise EventNotFound()
    top_score = ranked[0][1]
    second_score = ranked[1][1] if len(ranked) > 1 else -1.0
    top_is_clear = top_score >= 0.72 and top_score - second_score >= 0.18
    anchor_is_clear = bool(
        anchor and abs((events[0].start - anchor.astimezone(UTC)).total_seconds()) <= 900
        and (len(events) == 1 or abs((events[1].start - anchor.astimezone(UTC)).total_seconds()) > 900)
    )
    if len(events) > 1 and not top_is_clear and not anchor_is_clear:
        raise EventAmbiguous(
            [display_choice(event, user.timezone) for event in events[:5]]
        )
    event = events[0]
    payload: dict[str, Any] = {
        "schema_version": 1,
        "provider": provider,
        "event_id": event.id,
        "event_title": event.title,
        "original_start_iso": event.start.astimezone(UTC).isoformat(),
        "original_end_iso": event.end.astimezone(UTC).isoformat(),
        "attendees": event.attendees,
        "timezone": intent.timezone or user.timezone,
    }
    if intent.intent == "update_event":
        if not intent.start_iso and not intent.conference_requested:
            raise ValueError("Event update requires a new time or video service")
        new_start = event.start
        if intent.start_iso:
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
        if intent.conference_requested:
            payload["conference"] = (
                "yandex_telemost"
                if intent.conference_provider == "yandex"
                else "microsoft_teams"
                if intent.conference_provider == "microsoft"
                else "zoom"
                if intent.conference_provider == "zoom"
                else "google_meet"
                if intent.conference_provider == "google"
                else "none"
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
