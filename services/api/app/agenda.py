from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from .adapters import ProviderError, list_calendar_events
from .config import Settings
from .integrations import valid_access_token
from .models import LocalTask, Reminder, Timer, User


def agenda_window(user: User, days: int) -> tuple[datetime, datetime]:
    local_now = datetime.now(ZoneInfo(user.timezone))
    local_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    return local_start.astimezone(UTC), (local_start + timedelta(days=days)).astimezone(UTC)


async def collect_agenda(
    db: Session, settings: Settings, user: User, days: int
) -> tuple[datetime, datetime, list[dict]]:
    start, end = agenda_window(user, days)
    tasks = db.scalars(
        select(LocalTask).where(LocalTask.user_id == user.id, LocalTask.status == "open")
    ).all()
    items = [
        {"kind": "task", "source": "local", "id": row.id, "title": row.title,
         "start": row.due_at, "end": None, "status": row.status,
         "description": row.description, "priority": row.priority}
        for row in tasks if row.due_at is None or start <= row.due_at.astimezone(UTC) < end
    ]
    timers = db.scalars(
        select(Timer).where(Timer.user_id == user.id, Timer.status == "active")
    ).all()
    items.extend(
        {"kind": "timer", "source": "local", "id": row.id, "title": row.title,
         "start": row.starts_at, "end": row.ends_at, "status": row.status}
        for row in timers if start <= row.ends_at.astimezone(UTC) < end
    )
    reminders = db.scalars(
        select(Reminder).where(
            Reminder.user_id == user.id,
            Reminder.timer_id.is_(None),
            Reminder.status.in_(["scheduled", "retry", "processing"]),
            Reminder.due_at >= start,
            Reminder.due_at < end,
        )
    ).all()
    items.extend(
        {"kind": "reminder", "source": "local", "id": row.id, "title": row.title,
         "start": row.due_at, "end": None, "status": row.status, "channel": row.channel}
        for row in reminders
    )
    for provider in ("google", "microsoft"):
        try:
            token = await valid_access_token(db, settings, user, provider)
            events = await list_calendar_events(provider, token, start, end)
        except (LookupError, ProviderError):
            continue
        items.extend(provider_event(provider, row) for row in events)
    return start, end, items


def provider_event(provider: str, row: dict) -> dict:
    if provider == "google":
        points = row.get("conferenceData", {}).get("entryPoints", [])
        video = next(
            (item.get("uri") for item in points if item.get("entryPointType") == "video"), None
        )
        location = row.get("location")
        return {
            "kind": "event", "source": provider, "id": row.get("id"),
            "title": row.get("summary") or "Без названия", "start": row.get("start"),
            "end": row.get("end"), "status": row.get("status", "scheduled"),
            "attendees": [x.get("email") for x in row.get("attendees", []) if x.get("email")],
            "location": location, "join_url": row.get("hangoutLink") or video or https_url(location),
            "edit_url": https_url(row.get("htmlLink")),
            "reminder_minutes": google_reminder_minutes(row),
        }
    location = row.get("location", {}).get("displayName")
    return {
        "kind": "event", "source": provider, "id": row.get("id"),
        "title": row.get("subject") or "Без названия", "start": row.get("start"),
        "end": row.get("end"), "status": "scheduled",
        "attendees": [x.get("emailAddress", {}).get("address") for x in row.get("attendees", []) if x.get("emailAddress", {}).get("address")],
        "location": location,
        "join_url": row.get("onlineMeeting", {}).get("joinUrl") or https_url(location),
        "edit_url": https_url(row.get("webLink")),
        "reminder_minutes": row.get("reminderMinutesBeforeStart") if row.get("isReminderOn") else None,
    }


def https_url(value: object) -> str | None:
    return value if isinstance(value, str) and value.startswith("https://") else None


def google_reminder_minutes(row: dict) -> int | None:
    reminders = row.get("reminders", {})
    overrides = reminders.get("overrides", [])
    return overrides[0].get("minutes") if overrides else None
