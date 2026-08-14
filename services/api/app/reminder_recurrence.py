from datetime import UTC, date, datetime, time, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

from .models import Reminder

FREQUENCIES = {"daily", "weekly", "monthly"}


def validate_recurrence(value: dict | None) -> dict | None:
    if value is None:
        return None
    frequency = value.get("frequency")
    if frequency not in FREQUENCIES:
        raise ValueError("Unsupported reminder recurrence frequency")
    weekdays = value.get("weekdays") or []
    if any(not isinstance(day, int) or day < 0 or day > 6 for day in weekdays):
        raise ValueError("Reminder weekdays must be between 0 and 6")
    if frequency == "weekly" and not weekdays:
        raise ValueError("Weekly reminder requires weekdays")
    return {"frequency": frequency, "weekdays": sorted(set(weekdays))}


def next_occurrence(after: datetime, timezone: str, recurrence: dict) -> datetime:
    rule = validate_recurrence(recurrence)
    zone = ZoneInfo(timezone)
    local = after.astimezone(zone)
    wall_time = time(local.hour, local.minute, local.second, local.microsecond)
    frequency = rule["frequency"]
    if frequency == "daily":
        candidate = datetime.combine(local.date() + timedelta(days=1), wall_time, zone)
    elif frequency == "weekly":
        allowed = set(rule["weekdays"])
        day = local.date() + timedelta(days=1)
        while day.weekday() not in allowed:
            day += timedelta(days=1)
        candidate = datetime.combine(day, wall_time, zone)
    else:
        year, month = local.year, local.month + 1
        if month == 13:
            year, month = year + 1, 1
        day = min(local.day, _days_in_month(year, month))
        candidate = datetime.combine(
            local.date().replace(year=year, month=month, day=day), wall_time, zone
        )
    return candidate.astimezone(UTC)


def build_intent_reminders(db, user, intent, raw: str) -> tuple[list[Reminder], list[str]]:
    due = datetime.fromisoformat(intent.start_iso)
    recurrence = (
        {"frequency": intent.recurrence_frequency, "weekdays": intent.recurrence_weekdays or []}
        if intent.recurrence_frequency
        else None
    )
    zone = ZoneInfo(intent.timezone)
    times = intent.recurrence_times or [due.astimezone(zone).strftime("%H:%M")]
    series_id = str(uuid4()) if recurrence else None
    created = []
    for clock in times:
        hour, minute = (int(part) for part in clock.split(":"))
        occurrence = due.astimezone(zone).replace(hour=hour, minute=minute, second=0, microsecond=0)
        if (
            recurrence
            and recurrence["frequency"] == "weekly"
            and occurrence.weekday() not in recurrence["weekdays"]
        ):
            occurrence = next_occurrence(
                occurrence - timedelta(days=1), intent.timezone, recurrence
            ).astimezone(zone)
        if recurrence and occurrence.astimezone(UTC) < datetime.now(UTC):
            occurrence = next_occurrence(occurrence, intent.timezone, recurrence).astimezone(zone)
        row = Reminder(
            user_id=user.id,
            title=intent.title or raw,
            due_at=occurrence.astimezone(UTC),
            next_attempt_at=occurrence.astimezone(UTC),
            timezone=intent.timezone,
            recurrence_json=recurrence,
            series_id=series_id,
        )
        db.add(row)
        created.append(row)
    return created, times


def _days_in_month(year: int, month: int) -> int:
    following = date(year + (month == 12), month % 12 + 1, 1)
    return (following - timedelta(days=1)).day
