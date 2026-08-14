from datetime import UTC
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import audit
from ..database import get_db
from ..dependencies import current_user
from ..models import Reminder, User
from ..reminder_recurrence import validate_recurrence
from ..schemas import ReminderCreate, ReminderUpdate

router = APIRouter(prefix="/api/v1", tags=["reminders"])


def owned(db: Session, user: User, reminder_id: str) -> Reminder:
    row = db.scalar(
        select(Reminder).where(
            Reminder.id == reminder_id,
            Reminder.user_id == user.id,
            Reminder.task_id.is_(None),
            Reminder.timer_id.is_(None),
        )
    )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reminder not found")
    return row


def valid_scope(scope: str) -> None:
    if scope not in {"item", "series"}:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid reminder scope")


@router.get("/reminders")
def list_reminders(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return db.scalars(
        select(Reminder)
        .where(Reminder.user_id == user.id, Reminder.task_id.is_(None), Reminder.timer_id.is_(None))
        .order_by(Reminder.due_at)
        .limit(200)
    ).all()


@router.post("/reminders")
def create(
    body: ReminderCreate,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if body.due_at.tzinfo is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "due_at requires UTC offset")
    try:
        ZoneInfo(body.timezone)
        recurrence = validate_recurrence(body.recurrence)
    except (ValueError, ZoneInfoNotFoundError) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    due = body.due_at.astimezone(UTC)
    row = Reminder(
        user_id=user.id,
        title=body.title,
        due_at=due,
        next_attempt_at=due,
        timezone=body.timezone,
        channel=body.channel,
        recurrence_json=recurrence,
        series_id=str(uuid4()) if recurrence else None,
    )
    db.add(row)
    db.flush()
    audit(db, user, request, "reminder.created", "reminder", row.id)
    db.commit()
    return row


@router.put("/reminders/{reminder_id}")
def update(
    reminder_id: str,
    body: ReminderUpdate,
    request: Request,
    scope: str = "item",
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    row = owned(db, user, reminder_id)
    valid_scope(scope)
    targets = [row]
    if scope == "series" and row.series_id:
        targets = db.scalars(
            select(Reminder).where(Reminder.user_id == user.id, Reminder.series_id == row.series_id)
        ).all()
    if body.timezone is not None:
        try:
            ZoneInfo(body.timezone)
        except ZoneInfoNotFoundError as exc:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, "Unknown IANA timezone"
            ) from exc
        row.timezone = body.timezone
    if body.due_at is not None:
        if body.due_at.tzinfo is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "due_at requires UTC offset")
        row.due_at = body.due_at.astimezone(UTC)
        row.next_attempt_at = row.due_at
        row.status, row.attempts = "scheduled", 0
    if body.title is not None:
        for target in targets:
            target.title = body.title
    if "recurrence" in body.model_fields_set:
        try:
            row.recurrence_json = validate_recurrence(body.recurrence)
        except ValueError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
        row.series_id = row.series_id if row.recurrence_json else None
    if body.paused is not None:
        for target in targets:
            target.paused = body.paused
            if not body.paused and target.status in {"delivered", "failed"}:
                target.status, target.attempts, target.next_attempt_at = (
                    "scheduled",
                    0,
                    target.due_at,
                )
    audit(db, user, request, "reminder.updated", "reminder", row.id)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/reminders/{reminder_id}", status_code=204)
def remove(
    reminder_id: str,
    request: Request,
    scope: str = "item",
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    row = owned(db, user, reminder_id)
    valid_scope(scope)
    audit(db, user, request, "reminder.deleted", "reminder", row.id)
    rows = (
        db.scalars(
            select(Reminder).where(Reminder.user_id == user.id, Reminder.series_id == row.series_id)
        ).all()
        if scope == "series" and row.series_id
        else [row]
    )
    for target in rows:
        db.delete(target)
    db.commit()
