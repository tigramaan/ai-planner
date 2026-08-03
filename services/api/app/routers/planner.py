import hashlib
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..adapters import (
    ProviderError,
    cancel_calendar_event,
    create_calendar_event,
    default_event_window,
    list_calendar_events,
    send_email,
    update_calendar_event,
)
from ..audit import audit
from ..config import Settings, get_settings
from ..database import get_db
from ..dependencies import current_user
from ..integrations import valid_access_token
from ..models import AuditLog, LocalTask, PendingAction, PushSubscription, Reminder, Timer, User
from ..policy import action_status
from ..schemas import (
    PendingActionView,
    PushSubscriptionWrite,
    ReminderCreate,
    TaskCreate,
    TimerCreate,
)
from ..security import decrypt_json, encrypt_json

router = APIRouter(prefix="/api/v1", tags=["planner"])


@router.get("/tasks")
def tasks(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return db.scalars(
        select(LocalTask).where(LocalTask.user_id == user.id).order_by(LocalTask.created_at.desc())
    ).all()


@router.post("/tasks")
def create_task(
    body: TaskCreate,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    task = LocalTask(user_id=user.id, **body.model_dump())
    db.add(task)
    db.flush()
    audit(db, user, request, "task.created", "task", task.id, {"title": task.title})
    db.commit()
    return task


@router.post("/timers")
def create_timer(
    body: TimerCreate,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    start = datetime.now(UTC)
    timer = Timer(
        user_id=user.id,
        title=body.title,
        starts_at=start,
        ends_at=start + timedelta(seconds=body.duration_seconds),
    )
    db.add(timer)
    db.flush()
    audit(
        db,
        user,
        request,
        "timer.started",
        "timer",
        timer.id,
        {"duration_seconds": body.duration_seconds},
    )
    db.commit()
    return timer


@router.get("/reminders")
def reminders(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return db.scalars(
        select(Reminder)
        .where(Reminder.user_id == user.id)
        .order_by(Reminder.due_at.desc())
        .limit(200)
    ).all()


@router.post("/reminders")
def create_reminder(
    body: ReminderCreate,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if body.due_at.tzinfo is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "due_at requires UTC offset")
    try:
        ZoneInfo(body.timezone)
    except ZoneInfoNotFoundError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unknown IANA timezone") from exc
    due_at = body.due_at.astimezone(UTC)
    reminder = Reminder(
        user_id=user.id,
        title=body.title,
        due_at=due_at,
        next_attempt_at=due_at,
        timezone=body.timezone,
        channel=body.channel,
    )
    db.add(reminder)
    db.flush()
    audit(db, user, request, "reminder.created", "reminder", reminder.id)
    db.commit()
    return reminder


@router.get("/push/public-key")
def push_public_key(settings: Settings = Depends(get_settings)):
    if not settings.vapid_public_key:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Push is not configured")
    return {"public_key": settings.vapid_public_key}


@router.post("/push/subscriptions", status_code=201)
def subscribe_push(
    body: PushSubscriptionWrite,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    if not body.endpoint.startswith("https://"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Push endpoint must use HTTPS")
    endpoint_hash = hashlib.sha256(body.endpoint.encode()).hexdigest()
    subscription = db.scalar(
        select(PushSubscription).where(
            PushSubscription.user_id == user.id,
            PushSubscription.endpoint_hash == endpoint_hash,
        )
    )
    encrypted = encrypt_json(
        settings,
        body.model_dump(),
        f"push:{user.id}:{endpoint_hash}",
    )
    if subscription:
        subscription.encrypted_subscription = encrypted
        subscription.user_agent = request.headers.get("user-agent", "unknown")[:300]
    else:
        subscription = PushSubscription(
            user_id=user.id,
            endpoint_hash=endpoint_hash,
            encrypted_subscription=encrypted,
            user_agent=request.headers.get("user-agent", "unknown")[:300],
        )
        db.add(subscription)
    audit(db, user, request, "push.subscribed", "push_subscription", subscription.id)
    db.commit()
    return {"id": subscription.id, "configured": True}


@router.get("/today")
async def today(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    start, end = default_event_window()
    items = [
        {
            "kind": "task",
            "source": "local",
            "id": row.id,
            "title": row.title,
            "at": row.due_at,
            "status": row.status,
        }
        for row in db.scalars(
            select(LocalTask).where(LocalTask.user_id == user.id, LocalTask.status == "open")
        ).all()
    ]
    timers = db.scalars(
        select(Timer).where(Timer.user_id == user.id, Timer.status == "active")
    ).all()
    items.extend(
        {
            "kind": "timer",
            "source": "local",
            "id": row.id,
            "title": row.title,
            "at": row.ends_at,
            "status": row.status,
        }
        for row in timers
    )
    reminder_rows = db.scalars(
        select(Reminder).where(
            Reminder.user_id == user.id,
            Reminder.status.in_(["scheduled", "retry", "processing"]),
        )
    ).all()
    items.extend(
        {
            "kind": "reminder",
            "source": "local",
            "id": row.id,
            "title": row.title,
            "at": row.due_at,
            "status": row.status,
        }
        for row in reminder_rows
    )
    for provider in ("google", "microsoft"):
        try:
            token = await valid_access_token(db, settings, user, provider)
            events = await list_calendar_events(provider, token, start, end)
            items.extend(
                {
                    "kind": "event",
                    "source": provider,
                    "id": row.get("id"),
                    "title": row.get("summary") or row.get("subject"),
                    "at": row.get("start"),
                    "status": "scheduled",
                }
                for row in events
            )
        except (LookupError, ProviderError):
            continue
    return {"date": start.date(), "timezone": user.timezone, "items": items}


@router.get("/pending-actions", response_model=list[PendingActionView])
def pending_actions(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(PendingAction)
        .where(PendingAction.user_id == user.id)
        .order_by(PendingAction.expires_at.desc())
    ).all()
    return [
        PendingActionView(
            id=row.id,
            action_type=row.action_type,
            display_summary=row.display_summary,
            expires_at=row.expires_at,
            status=action_status(row),
            result=row.result_json,
        )
        for row in rows
    ]


@router.post("/pending-actions/{action_id}/confirm")
async def confirm(
    action_id: str,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    action = db.get(PendingAction, action_id)
    if not action or action.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pending action not found")
    current = action_status(action)
    if current == "executed":
        return {"status": "executed", "result": action.result_json}
    if current != "pending":
        raise HTTPException(status.HTTP_409_CONFLICT, f"Action is {current}")
    payload = decrypt_json(
        settings, action.payload_encrypted, f"pending:{action.id}:{action.payload_hash}"
    )
    action.confirmed_at = datetime.now(UTC)
    if action.action_type == "create_meeting":
        provider = payload.get("provider", "google")
        token = await valid_access_token(db, settings, user, provider)
        payload["idempotency_key"] = action.idempotency_key
        result = await create_calendar_event(provider, token, payload)
    elif action.action_type in {"update_event", "add_event_participants"}:
        provider = payload.get("provider", "google")
        token = await valid_access_token(db, settings, user, provider)
        result = await update_calendar_event(provider, token, payload)
    elif action.action_type == "cancel_event":
        provider = payload.get("provider", "google")
        token = await valid_access_token(db, settings, user, provider)
        result = await cancel_calendar_event(provider, token, payload["event_id"])
    elif action.action_type == "send_email":
        provider = payload.get("provider", "google")
        token = await valid_access_token(db, settings, user, provider)
        result = await send_email(provider, token, payload)
    else:
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "Confirmed tool is not implemented")
    action.result_json = {
        "id": result.get("id"),
        "link": result.get("htmlLink") or (result.get("onlineMeeting") or {}).get("joinUrl"),
        "status": result.get("status"),
    }
    action.executed_at = datetime.now(UTC)
    audit(
        db,
        user,
        request,
        "pending_action.executed",
        "pending_action",
        action.id,
        {"action_type": action.action_type},
    )
    db.commit()
    return {"status": "executed", "result": action.result_json}


@router.post("/pending-actions/{action_id}/cancel", status_code=204)
def cancel(
    action_id: str,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    action = db.get(PendingAction, action_id)
    if not action or action.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pending action not found")
    if action_status(action) != "pending":
        raise HTTPException(status.HTTP_409_CONFLICT, "Action is no longer pending")
    action.cancelled_at = datetime.now(UTC)
    audit(db, user, request, "pending_action.cancelled", "pending_action", action.id)
    db.commit()


@router.get("/audit")
def audit_log(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return db.scalars(
        select(AuditLog)
        .where(AuditLog.user_id == user.id)
        .order_by(AuditLog.created_at.desc())
        .limit(200)
    ).all()
