from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import LocalTask, PushSubscription, Reminder, Timer, User


def push_ready(db: Session, user: User) -> bool:
    return db.scalar(
        select(PushSubscription.id).where(PushSubscription.user_id == user.id).limit(1)
    ) is not None


def _timer_title(user: User, timer: Timer) -> str:
    if user.locale.startswith("ru"):
        return f"Таймер «{timer.title}» завершён"
    return f'Timer "{timer.title}" finished'


def _task_title(user: User, task: LocalTask) -> str:
    if user.locale.startswith("ru"):
        return f"Срок задачи «{task.title}»"
    return f'Task "{task.title}" is due'


def _reset(reminder: Reminder, due_at: datetime) -> None:
    reminder.due_at = due_at
    reminder.next_attempt_at = due_at
    reminder.status = "scheduled"
    reminder.attempts = 0
    reminder.delivered_at = None
    reminder.last_error = None


def schedule_timer_notification(
    db: Session, user: User, timer: Timer, *, reset: bool = True
) -> bool:
    reminder = db.scalar(select(Reminder).where(Reminder.timer_id == timer.id))
    if reminder is None:
        reminder = Reminder(
            user_id=user.id,
            timer_id=timer.id,
            title=_timer_title(user, timer),
            due_at=timer.ends_at,
            next_attempt_at=timer.ends_at,
            timezone=user.timezone,
            channel="push",
        )
        db.add(reminder)
    else:
        reminder.title = _timer_title(user, timer)
        reminder.timezone = user.timezone
        if reset:
            _reset(reminder, timer.ends_at)
    return push_ready(db, user)


def delete_timer_notification(db: Session, timer: Timer) -> None:
    reminder = db.scalar(select(Reminder).where(Reminder.timer_id == timer.id))
    if reminder is not None:
        db.delete(reminder)


def schedule_task_notification(
    db: Session, user: User, task: LocalTask, *, reset: bool = True
) -> bool:
    reminder = db.scalar(select(Reminder).where(Reminder.task_id == task.id))
    if task.due_at is None or task.status != "open":
        if reminder is not None:
            db.delete(reminder)
        return push_ready(db, user)
    if reminder is None:
        if task.due_at.astimezone(UTC) <= datetime.now(UTC):
            return push_ready(db, user)
        reminder = Reminder(
            user_id=user.id,
            task_id=task.id,
            title=_task_title(user, task),
            due_at=task.due_at,
            next_attempt_at=task.due_at,
            timezone=task.timezone,
            channel="push",
        )
        db.add(reminder)
    else:
        reminder.title = _task_title(user, task)
        reminder.timezone = task.timezone
        if reset:
            _reset(reminder, task.due_at)
    return push_ready(db, user)


def delete_task_notification(db: Session, task: LocalTask) -> None:
    reminder = db.scalar(select(Reminder).where(Reminder.task_id == task.id))
    if reminder is not None:
        db.delete(reminder)
