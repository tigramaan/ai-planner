from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..audit import audit
from ..database import get_db
from ..dependencies import current_user
from ..local_notifications import (
    delete_task_notification,
    delete_timer_notification,
    schedule_task_notification,
    schedule_timer_notification,
)
from ..models import LocalTask, TaskParticipant, Timer, User
from ..schemas import TaskCreate, TaskUpdate, TimerCreate, TimerUpdate
from ..task_collaboration import accessible_task, add_activity, owner_task, task_view

router = APIRouter(prefix="/api/v1", tags=["local-planner"])


def owned(row_type, row_id: str, user: User, db: Session):
    row = db.get(row_type, row_id)
    if not row or row.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{row_type.__name__} not found")
    return row


@router.get("/tasks")
def tasks(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(LocalTask)
        .outerjoin(TaskParticipant, TaskParticipant.task_id == LocalTask.id)
        .where(or_(LocalTask.user_id == user.id, TaskParticipant.user_id == user.id))
        .distinct()
        .order_by(LocalTask.created_at.desc())
        .limit(500)
    ).all()
    return [task_view(db, row, user) for row in rows]


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
    add_activity(db, task, user, "created")
    schedule_task_notification(db, user, task)
    audit(db, user, request, "task.created", "task", task.id, {"title": task.title})
    db.commit()
    return task_view(db, task, user)


@router.put("/tasks/{task_id}")
def update_task(
    task_id: str,
    body: TaskUpdate,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    task = accessible_task(db, task_id, user)
    changes = body.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(task, field, value)
    owner = db.get(User, task.user_id)
    schedule_task_notification(db, owner, task, reset="due_at" in changes or changes.get("status") == "open")
    add_activity(db, task, user, "updated", {"fields": sorted(changes)})
    audit(
        db,
        user,
        request,
        "task.updated",
        "task",
        task.id,
        {"fields": sorted(changes), "status": task.status},
    )
    db.commit()
    db.refresh(task)
    return task_view(db, task, user)


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: str,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    task = owner_task(db, task_id, user)
    audit(db, user, request, "task.deleted", "task", task.id, {"title": task.title})
    delete_task_notification(db, task)
    db.delete(task)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
    schedule_timer_notification(db, user, timer, reset=body.duration_seconds is not None)
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


@router.get("/timers")
def timers(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return db.scalars(
        select(Timer)
        .where(Timer.user_id == user.id, Timer.status == "active")
        .order_by(Timer.ends_at)
        .limit(20)
    ).all()


@router.put("/timers/{timer_id}")
def update_timer(
    timer_id: str,
    body: TimerUpdate,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    timer = owned(Timer, timer_id, user, db)
    if body.title is not None:
        timer.title = body.title
    if body.duration_seconds is not None:
        timer.starts_at = datetime.now(UTC)
        timer.ends_at = timer.starts_at + timedelta(seconds=body.duration_seconds)
        timer.status = "active"
    schedule_timer_notification(db, user, timer)
    audit(db, user, request, "timer.updated", "timer", timer.id)
    db.commit()
    db.refresh(timer)
    return timer


@router.delete("/timers/{timer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_timer(
    timer_id: str,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    timer = owned(Timer, timer_id, user, db)
    audit(db, user, request, "timer.deleted", "timer", timer.id, {"title": timer.title})
    delete_timer_notification(db, timer)
    db.delete(timer)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
