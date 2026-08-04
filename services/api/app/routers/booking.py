import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..adapters import (
    ProviderError,
    create_calendar_event,
    create_teams_online_meeting,
    create_zoom_meeting,
    list_calendar_events,
)
from ..audit import audit
from ..booking import (
    candidate_slots,
    lead_digest,
    policy_window,
    provider_busy,
    request_digest,
    timezone,
)
from ..booking_schemas import BookingCreate, BookingKeyCreate, BookingPolicyWrite
from ..conference_fallbacks import read_fallback_url
from ..config import Settings, get_settings
from ..database import get_db
from ..dependencies import current_user
from ..integrations import valid_access_token
from ..models import Booking, BookingApiKey, BookingPolicy, User
from ..security import encrypt_json, token_hash

router = APIRouter(tags=["booking"])


def policy_for(db: Session, user: User) -> BookingPolicy:
    policy = db.get(BookingPolicy, user.id)
    if not policy:
        policy = BookingPolicy(user_id=user.id)
        db.add(policy)
        db.flush()
    return policy


def policy_view(policy: BookingPolicy, keys: list[BookingApiKey] | None = None) -> dict:
    result = {
        column.name: getattr(policy, column.name) for column in BookingPolicy.__table__.columns
    }
    result["keys"] = [
        {
            "id": key.id,
            "name": key.name,
            "prefix": key.key_prefix,
            "created_at": key.created_at,
            "last_used_at": key.last_used_at,
            "revoked_at": key.revoked_at,
        }
        for key in (keys or [])
    ]
    return result


@router.get("/api/v1/booking/settings")
def get_booking_settings(user: User = Depends(current_user), db: Session = Depends(get_db)):
    policy = policy_for(db, user)
    db.commit()
    keys = db.scalars(
        select(BookingApiKey)
        .where(BookingApiKey.user_id == user.id)
        .order_by(BookingApiKey.created_at.desc())
    ).all()
    return policy_view(policy, list(keys))


@router.put("/api/v1/booking/settings")
def update_booking_settings(
    body: BookingPolicyWrite,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if body.work_start >= body.work_end:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "work_start must be before work_end"
        )
    policy = policy_for(db, user)
    for key, value in body.model_dump().items():
        setattr(policy, key, value)
    policy.updated_at = datetime.now(UTC)
    audit(db, user, request, "booking.policy_updated", "booking_policy", user.id)
    db.commit()
    return policy_view(policy)


@router.post("/api/v1/booking/keys", status_code=201)
def create_booking_key(
    body: BookingKeyCreate,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    raw = f"aipb_{secrets.token_urlsafe(32)}"
    key = BookingApiKey(
        user_id=user.id, name=body.name.strip(), key_prefix=raw[:12], key_hash=token_hash(raw)
    )
    db.add(key)
    db.flush()
    audit(db, user, request, "booking.key_created", "booking_api_key", key.id)
    db.commit()
    return {
        "id": key.id,
        "name": key.name,
        "prefix": key.key_prefix,
        "api_key": raw,
        "created_at": key.created_at,
    }


@router.delete("/api/v1/booking/keys/{key_id}", status_code=204)
def revoke_booking_key(
    key_id: str,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    key = db.scalar(
        select(BookingApiKey).where(BookingApiKey.id == key_id, BookingApiKey.user_id == user.id)
    )
    if not key:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking key not found")
    key.revoked_at = datetime.now(UTC)
    audit(db, user, request, "booking.key_revoked", "booking_api_key", key.id)
    db.commit()


def api_context(
    authorization: str | None, db: Session
) -> tuple[BookingApiKey, User, BookingPolicy]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing booking API key")
    key = db.scalar(
        select(BookingApiKey).where(BookingApiKey.key_hash == token_hash(authorization[7:]))
    )
    if not key or key.revoked_at:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid booking API key")
    user, policy = db.get(User, key.user_id), db.get(BookingPolicy, key.user_id)
    if not user or not policy or not policy.enabled:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Booking API is disabled")
    key.last_used_at = datetime.now(UTC)
    return key, user, policy


async def availability_rows(
    db: Session, settings: Settings, user: User, policy: BookingPolicy, requested_from: datetime
) -> list[tuple[datetime, datetime]]:
    if requested_from.tzinfo is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "from requires UTC offset")
    now = datetime.now(UTC)
    minimum, maximum = policy_window(policy, user, now)
    start = max(requested_from.astimezone(UTC), minimum)
    provider = user.default_calendar
    if provider not in {"google", "microsoft"}:
        raise HTTPException(status.HTTP_409_CONFLICT, "Default calendar does not support booking")
    try:
        token = await valid_access_token(db, settings, user, provider)
        events = await list_calendar_events(
            provider, token, start - timedelta(hours=4), maximum + timedelta(hours=4)
        )
    except (LookupError, ProviderError) as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Calendar is unavailable") from exc
    local = db.scalars(
        select(Booking).where(
            Booking.user_id == user.id,
            Booking.status.in_(["creating", "created"]),
            Booking.start_at < maximum,
            Booking.end_at > start,
        )
    ).all()
    busy = provider_busy(events) + [
        (
            row.start_at.replace(tzinfo=UTC)
            if row.start_at.tzinfo is None
            else row.start_at.astimezone(UTC),
            row.end_at.replace(tzinfo=UTC)
            if row.end_at.tzinfo is None
            else row.end_at.astimezone(UTC),
        )
        for row in local
        if row.status == "creating"
    ]
    counts: dict[str, int] = {}
    owner_zone = timezone(user.timezone)
    for row in local:
        day = (
            (row.start_at.replace(tzinfo=UTC) if row.start_at.tzinfo is None else row.start_at)
            .astimezone(owner_zone)
            .date()
            .isoformat()
        )
        counts[day] = counts.get(day, 0) + 1
    return candidate_slots(policy, user, start, maximum, busy, counts)


@router.get("/booking/v1/availability")
async def availability(
    requested_from: datetime = Query(alias="from"),
    requested_timezone: str = Query(alias="timezone"),
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    _, user, policy = api_context(authorization, db)
    zone = timezone(requested_timezone)
    slots = await availability_rows(db, settings, user, policy, requested_from)
    db.commit()
    return {
        "timezone": requested_timezone,
        "duration_minutes": policy.duration_minutes,
        "slots": [
            {"start": start.astimezone(zone).isoformat(), "end": end.astimezone(zone).isoformat()}
            for start, end in slots
        ],
    }


def booking_view(row: Booking) -> dict:
    return {
        "id": row.id,
        "status": row.status,
        "start": row.start_at,
        "end": row.end_at,
        "timezone": row.timezone,
        "provider": row.provider,
        "event": row.result_json,
    }


@router.post("/booking/v1/bookings", status_code=201)
async def create_booking(
    body: BookingCreate,
    authorization: str | None = Header(default=None),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    if not idempotency_key or not 8 <= len(idempotency_key) <= 100:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Idempotency-Key must be 8-100 characters"
        )
    if body.start.tzinfo is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "start requires UTC offset")
    timezone(body.timezone)
    key, user, policy = api_context(authorization, db)
    payload = body.model_dump(mode="json")
    digest = request_digest(payload)
    previous = db.scalar(
        select(Booking).where(
            Booking.api_key_id == key.id, Booking.idempotency_key == idempotency_key
        )
    )
    if previous:
        if previous.request_hash != digest:
            raise HTTPException(status.HTTP_409_CONFLICT, "Idempotency-Key payload mismatch")
        return booking_view(previous)
    policy = db.scalar(
        select(BookingPolicy).where(BookingPolicy.user_id == user.id).with_for_update()
    )
    if policy is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Booking API is disabled")
    lead_hash = lead_digest(user.id, body.lead_id)
    successes = (
        db.scalar(
            select(func.count())
            .select_from(Booking)
            .where(
                Booking.user_id == user.id,
                Booking.lead_hash == lead_hash,
                Booking.status.in_(["creating", "created"]),
            )
        )
        or 0
    )
    if successes >= 3:
        raise HTTPException(status.HTTP_409_CONFLICT, "booking_attempt_limit_reached")
    requested_start = body.start.astimezone(UTC)
    slots = await availability_rows(db, settings, user, policy, requested_start)
    if not slots or slots[0][0] != requested_start:
        raise HTTPException(status.HTTP_409_CONFLICT, "slot_unavailable")
    requested_end = requested_start + timedelta(minutes=policy.duration_minutes)
    if user.default_calendar == "microsoft" and user.default_conference == "google":
        raise HTTPException(status.HTTP_409_CONFLICT, "conference_not_supported_by_calendar")
    if user.default_conference == "yandex" and not read_fallback_url(
        settings, user, "yandex_telemost"
    ):
        raise HTTPException(status.HTTP_409_CONFLICT, "conference_fallback_not_configured")
    row = Booking(
        user_id=user.id,
        api_key_id=key.id,
        lead_hash=lead_hash,
        idempotency_key=idempotency_key,
        request_hash=digest,
        slot_lock=f"{user.id}:{requested_start.isoformat()}",
        contact_encrypted=encrypt_json(settings, payload, f"booking:{user.id}:{digest}"),
        start_at=requested_start,
        end_at=requested_end,
        timezone=body.timezone,
        provider=user.default_calendar,
        status="creating",
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "slot_unavailable") from exc
    conference = {"google": "google_meet", "microsoft": "microsoft_teams", "none": "none"}.get(
        user.default_conference, "none"
    )
    external_url = (
        read_fallback_url(settings, user, "yandex_telemost")
        if user.default_conference == "yandex"
        else None
    )
    event_payload = {
        "title": policy.title_template.format(name=body.name),
        "start_iso": requested_start.isoformat(),
        "end_iso": requested_end.isoformat(),
        "timezone": body.timezone,
        "attendees": [str(body.email)],
        "conference": conference,
        "external_join_url": external_url,
        "idempotency_key": idempotency_key,
        "reminder_minutes": user.default_reminder_minutes,
    }
    try:
        token = await valid_access_token(db, settings, user, user.default_calendar)
        if user.default_conference == "microsoft" and user.default_calendar == "google":
            event_payload["conference"] = "none"
            try:
                teams_token = await valid_access_token(db, settings, user, "microsoft")
                teams = await create_teams_online_meeting(teams_token, event_payload)
                event_payload["external_join_url"] = teams.get("joinWebUrl")
            except (LookupError, ProviderError):
                event_payload["external_join_url"] = read_fallback_url(
                    settings, user, "microsoft_teams"
                )
            if not event_payload["external_join_url"]:
                raise ProviderError("Microsoft returned no Teams join URL")
        elif user.default_conference == "zoom":
            zoom_token = await valid_access_token(db, settings, user, "zoom")
            zoom = await create_zoom_meeting(zoom_token, event_payload)
            event_payload["external_join_url"] = zoom.get("join_url")
        result = await create_calendar_event(user.default_calendar, token, event_payload)
        if not result.get("id"):
            raise ProviderError("Calendar returned no event id")
    except Exception as exc:
        db.delete(row)
        db.commit()
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Calendar booking failed") from exc
    row.status, row.slot_lock, row.provider_event_id, row.result_json = (
        "created",
        None,
        str(result["id"]),
        {"id": result["id"], "htmlLink": result.get("htmlLink"), "webLink": result.get("webLink")},
    )
    db.commit()
    return booking_view(row)


@router.get("/booking/v1/bookings/{booking_id}")
def get_booking(
    booking_id: str, authorization: str | None = Header(default=None), db: Session = Depends(get_db)
):
    _, user, _ = api_context(authorization, db)
    row = db.scalar(select(Booking).where(Booking.id == booking_id, Booking.user_id == user.id))
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")
    db.commit()
    return booking_view(row)
