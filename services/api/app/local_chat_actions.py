from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import LocalTask, Timer, User
from .schemas import Intent
from .timer_notifications import delete_timer_notification, schedule_timer_notification

LOCAL_INTENTS = {
    "create_task",
    "update_task",
    "complete_task",
    "reopen_task",
    "delete_task",
    "start_timer",
    "update_timer",
    "cancel_timer",
}


def recent_match(db: Session, row_type, user: User, query: str):
    order = row_type.created_at if row_type is LocalTask else row_type.starts_at
    return next(
        (
            row
            for row in db.scalars(
                select(row_type)
                .where(row_type.user_id == user.id)
                .order_by(order.desc())
                .limit(500)
            )
            if query in row.title.casefold()
        ),
        None,
    )


def task_action(db: Session, user: User, intent: Intent, raw: str, ru: bool) -> str:
    if intent.intent == "create_task":
        due_at = datetime.fromisoformat(intent.start_iso) if intent.start_iso else None
        if due_at and due_at.tzinfo is None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, "Task due time requires UTC offset"
            )
        task = LocalTask(
            user_id=user.id,
            title=intent.title or raw,
            description=intent.body or "",
            due_at=due_at,
            timezone=intent.timezone or user.timezone,
            priority=intent.priority or "normal",
        )
        db.add(task)
        return f"Задача «{task.title}» создана." if ru else f'Task "{task.title}" created.'
    query = (intent.event_query or intent.title or "").casefold().strip()
    task = recent_match(db, LocalTask, user, query) if query else None
    if not task:
        return (
            "Задача не найдена. Укажите её название."
            if ru
            else "Task not found. Specify its title."
        )
    if intent.intent == "delete_task":
        title = task.title
        db.delete(task)
        return f"Задача «{title}» удалена." if ru else f'Task "{title}" deleted.'
    if intent.intent == "complete_task":
        task.status = "completed"
        return f"Задача «{task.title}» выполнена." if ru else f'Task "{task.title}" completed.'
    if intent.intent == "reopen_task":
        task.status = "open"
        return f"Задача «{task.title}» возвращена в работу." if ru else f'Task "{task.title}" reopened.'
    if intent.title:
        task.title = intent.title
    if intent.body is not None:
        task.description = intent.body
    if intent.priority:
        task.priority = intent.priority
    if intent.start_iso:
        due_at = datetime.fromisoformat(intent.start_iso)
        if due_at.tzinfo is None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, "Task due time requires UTC offset"
            )
        task.due_at = due_at
    return f"Задача «{task.title}» изменена." if ru else f'Task "{task.title}" updated.'


def timer_action(db: Session, user: User, intent: Intent, ru: bool) -> str:
    if intent.intent == "start_timer":
        seconds = (intent.duration_minutes or 25) * 60
        timer = Timer(
            user_id=user.id,
            title=intent.title or ("Таймер" if ru else "Timer"),
            ends_at=datetime.now(UTC) + timedelta(seconds=seconds),
        )
        db.add(timer)
        db.flush()
        push_ready = schedule_timer_notification(db, user, timer)
        answer = (
            f"Таймер запущен на {seconds // 60} минут."
            if ru
            else f"Timer started for {seconds // 60} minutes."
        )
        if not push_ready:
            answer += (
                " Чтобы получить сигнал, включите push-уведомления в Настройках."
                if ru
                else " Enable push notifications in Settings to receive the alert."
            )
        return answer
    query = (intent.event_query or intent.title or "").casefold().strip()
    timer = recent_match(db, Timer, user, query) if query else None
    if not timer:
        return (
            "Таймер не найден. Укажите его название."
            if ru
            else "Timer not found. Specify its title."
        )
    if intent.intent == "cancel_timer":
        title = timer.title
        delete_timer_notification(db, timer)
        db.delete(timer)
        return f"Таймер «{title}» удалён." if ru else f'Timer "{title}" deleted.'
    seconds = (intent.duration_minutes or 25) * 60
    timer.title = intent.title or timer.title
    timer.starts_at = datetime.now(UTC)
    timer.ends_at = timer.starts_at + timedelta(seconds=seconds)
    timer.status = "active"
    push_ready = schedule_timer_notification(db, user, timer)
    answer = (
        f"Таймер «{timer.title}» перезапущен на {seconds // 60} минут."
        if ru
        else f'Timer "{timer.title}" restarted for {seconds // 60} minutes.'
    )
    if not push_ready:
        answer += (
            " Чтобы получить сигнал, включите push-уведомления в Настройках."
            if ru
            else " Enable push notifications in Settings to receive the alert."
        )
    return answer


def handle_local_intent(db: Session, user: User, intent: Intent, raw: str, ru: bool) -> str:
    if "task" in intent.intent:
        return task_action(db, user, intent, raw, ru)
    return timer_action(db, user, intent, ru)
