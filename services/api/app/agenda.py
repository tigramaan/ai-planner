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
         "at": row.due_at, "status": row.status}
        for row in tasks if row.due_at is None or start <= row.due_at.astimezone(UTC) < end
    ]
    timers = db.scalars(
        select(Timer).where(Timer.user_id == user.id, Timer.status == "active")
    ).all()
    items.extend(
        {"kind": "timer", "source": "local", "id": row.id, "title": row.title,
         "at": row.ends_at, "status": row.status}
        for row in timers if start <= row.ends_at.astimezone(UTC) < end
    )
    reminders = db.scalars(
        select(Reminder).where(
            Reminder.user_id == user.id,
            Reminder.status.in_(["scheduled", "retry", "processing"]),
            Reminder.due_at >= start,
            Reminder.due_at < end,
        )
    ).all()
    items.extend(
        {"kind": "reminder", "source": "local", "id": row.id, "title": row.title,
         "at": row.due_at, "status": row.status}
        for row in reminders
    )
    for provider in ("google", "microsoft"):
        try:
            token = await valid_access_token(db, settings, user, provider)
            events = await list_calendar_events(provider, token, start, end)
        except (LookupError, ProviderError):
            continue
        items.extend(
            {"kind": "event", "source": provider, "id": row.get("id"),
             "title": row.get("summary") or row.get("subject"), "at": row.get("start"),
             "status": "scheduled"}
            for row in events
        )
    return start, end, items
