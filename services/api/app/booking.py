import hashlib
import json
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException, status

from .models import BookingPolicy, User


def timezone(value: str) -> ZoneInfo:
    try:
        return ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unknown IANA timezone") from exc


def request_digest(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def lead_digest(user_id: str, lead_id: str) -> str:
    return hashlib.sha256(f"{user_id}:{lead_id}".encode()).hexdigest()


def policy_window(policy: BookingPolicy, user: User, now: datetime) -> tuple[datetime, datetime]:
    start = now + timedelta(minutes=policy.minimum_notice_minutes)
    end = now + timedelta(days=policy.horizon_days)
    return start.astimezone(UTC), end.astimezone(UTC)


def provider_busy(events: list[dict]) -> list[tuple[datetime, datetime]]:
    rows = []
    for event in events:
        if event.get("status") == "cancelled" or event.get("isCancelled"):
            continue
        start = event.get("start", {})
        end = event.get("end", {})
        start_value = start.get("dateTime") if isinstance(start, dict) else None
        end_value = end.get("dateTime") if isinstance(end, dict) else None
        if start_value and end_value:
            rows.append(
                (
                    datetime.fromisoformat(start_value).astimezone(UTC),
                    datetime.fromisoformat(end_value).astimezone(UTC),
                )
            )
    return rows


def overlaps(start: datetime, end: datetime, busy: list[tuple[datetime, datetime]]) -> bool:
    return any(start < busy_end and end > busy_start for busy_start, busy_end in busy)


def candidate_slots(
    policy: BookingPolicy,
    user: User,
    start: datetime,
    end: datetime,
    busy: list[tuple[datetime, datetime]],
    daily_counts: dict[str, int],
) -> list[tuple[datetime, datetime]]:
    owner_zone = timezone(user.timezone)
    cursor_day = start.astimezone(owner_zone).date()
    last_day = end.astimezone(owner_zone).date()
    work_start = time.fromisoformat(policy.work_start)
    work_end = time.fromisoformat(policy.work_end)
    duration = timedelta(minutes=policy.duration_minutes)
    before = timedelta(minutes=policy.buffer_before_minutes)
    after = timedelta(minutes=policy.buffer_after_minutes)
    slots = []
    while cursor_day <= last_day and len(slots) < 500:
        day_key = cursor_day.isoformat()
        if (
            cursor_day.weekday() in policy.workdays
            and daily_counts.get(day_key, 0) < policy.max_per_day
        ):
            cursor = datetime.combine(cursor_day, work_start, owner_zone)
            day_end = datetime.combine(cursor_day, work_end, owner_zone)
            while cursor + duration <= day_end:
                slot_start, slot_end = cursor.astimezone(UTC), (cursor + duration).astimezone(UTC)
                if (
                    slot_start >= start
                    and slot_end <= end
                    and not overlaps(slot_start - before, slot_end + after, busy)
                ):
                    slots.append((slot_start, slot_end))
                cursor += duration
        cursor_day += timedelta(days=1)
    return slots
