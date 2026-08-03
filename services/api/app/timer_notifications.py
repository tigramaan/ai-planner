from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import PushSubscription, Reminder, Timer, User


def _title(user: User, timer: Timer) -> str:
    if user.locale.startswith("ru"):
        return f"Таймер «{timer.title}» завершён"
    return f'Timer "{timer.title}" finished'


def schedule_timer_notification(db: Session, user: User, timer: Timer) -> bool:
    reminder = db.scalar(select(Reminder).where(Reminder.timer_id == timer.id))
    if reminder is None:
        reminder = Reminder(
            user_id=user.id,
            timer_id=timer.id,
            title=_title(user, timer),
            due_at=timer.ends_at,
            next_attempt_at=timer.ends_at,
            timezone=user.timezone,
            channel="push",
        )
        db.add(reminder)
    else:
        reminder.title = _title(user, timer)
        reminder.due_at = timer.ends_at
        reminder.next_attempt_at = timer.ends_at
        reminder.timezone = user.timezone
        reminder.channel = "push"
        reminder.status = "scheduled"
        reminder.attempts = 0
        reminder.delivered_at = None
        reminder.last_error = None
    return db.scalar(
        select(PushSubscription.id).where(PushSubscription.user_id == user.id).limit(1)
    ) is not None


def delete_timer_notification(db: Session, timer: Timer) -> None:
    reminder = db.scalar(select(Reminder).where(Reminder.timer_id == timer.id))
    if reminder is not None:
        db.delete(reminder)
