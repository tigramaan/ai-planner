from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .local_notifications import (
    delete_task_notification,
    delete_timer_notification,
    schedule_task_notification,
    schedule_timer_notification,
)
from .models import LocalTask, Timer, User
from .schemas import Intent

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


def duration_label(minutes: int, ru: bool) -> str:
    if not ru:
        return f"{minutes} {'minute' if minutes == 1 else 'minutes'}"
    if minutes % 10 == 1 and minutes % 100 != 11:
        unit = "минуту"
    elif minutes % 10 in {2, 3, 4} and minutes % 100 not in {12, 13, 14}:
        unit = "минуты"
    else:
        unit = "минут"
    return f"{minutes} {unit}"


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
        db.flush()
        push_is_ready = schedule_task_notification(db, user, task)
        answer = f"Задача «{task.title}» создана." if ru else f'Task "{task.title}" created.'
        if task.due_at and not push_is_ready:
            answer += (
                " Чтобы получить напоминание о сроке, включите уведомления в Настройках."
                if ru
                else " Enable notifications in Settings to receive the due-time reminder."
            )
        return answer
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
        delete_task_notification(db, task)
        db.delete(task)
        return f"Задача «{title}» удалена." if ru else f'Task "{title}" deleted.'
    if intent.intent == "complete_task":
        task.status = "completed"
        delete_task_notification(db, task)
        return f"Задача «{task.title}» выполнена." if ru else f'Task "{task.title}" completed.'
    if intent.intent == "reopen_task":
        task.status = "open"
        push_is_ready = schedule_task_notification(db, user, task)
        answer = f"Задача «{task.title}» возвращена в работу." if ru else f'Task "{task.title}" reopened.'
        if task.due_at and not push_is_ready:
            answer += (
                " Чтобы получить напоминание о сроке, включите уведомления в Настройках."
                if ru
                else " Enable notifications in Settings to receive the due-time reminder."
            )
        return answer
    due_changed = bool(intent.start_iso)
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
    push_is_ready = schedule_task_notification(db, user, task, reset=due_changed)
    answer = f"Задача «{task.title}» изменена." if ru else f'Task "{task.title}" updated.'
    if task.due_at and not push_is_ready:
        answer += (
            " Чтобы получить напоминание о сроке, включите уведомления в Настройках."
            if ru
            else " Enable notifications in Settings to receive the due-time reminder."
        )
    return answer


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
        end_time = timer.ends_at.astimezone(ZoneInfo(user.timezone)).strftime("%H:%M")
        duration = duration_label(seconds // 60, ru)
        answer = (
            f"Таймер «{timer.title}» запущен на {duration}, до {end_time}."
            if ru
            else f'Timer "{timer.title}" started for {duration}, until {end_time}.'
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
        f"Таймер «{timer.title}» перезапущен на {duration_label(seconds // 60, ru)}."
        if ru
        else f'Timer "{timer.title}" restarted for {duration_label(seconds // 60, ru)}.'
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
