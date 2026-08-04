from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .models import LocalTask, TaskActivity, TaskChecklistItem, TaskParticipant, User


def accessible_task(db: Session, task_id: str, user: User) -> LocalTask:
    task = db.scalar(
        select(LocalTask)
        .outerjoin(TaskParticipant, TaskParticipant.task_id == LocalTask.id)
        .where(
            LocalTask.id == task_id,
            or_(LocalTask.user_id == user.id, TaskParticipant.user_id == user.id),
        )
    )
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "LocalTask not found")
    return task


def owner_task(db: Session, task_id: str, user: User) -> LocalTask:
    task = db.scalar(
        select(LocalTask).where(LocalTask.id == task_id, LocalTask.user_id == user.id)
    )
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "LocalTask not found")
    return task


def add_activity(
    db: Session, task: LocalTask, user: User, action: str, details: dict | None = None
) -> None:
    db.add(
        TaskActivity(
            task_id=task.id,
            actor_user_id=user.id,
            action=action,
            details_json=details or {},
        )
    )


def task_view(db: Session, task: LocalTask, viewer: User) -> dict:
    participant_rows = db.execute(
        select(TaskParticipant, User)
        .join(User, User.id == TaskParticipant.user_id)
        .where(TaskParticipant.task_id == task.id)
        .order_by(User.email)
    ).all()
    checklist = db.scalars(
        select(TaskChecklistItem)
        .where(TaskChecklistItem.task_id == task.id)
        .order_by(TaskChecklistItem.position, TaskChecklistItem.created_at)
    ).all()
    actor = User.__table__.alias("actor")
    activities = db.execute(
        select(TaskActivity, actor.c.email)
        .join(actor, actor.c.id == TaskActivity.actor_user_id)
        .where(TaskActivity.task_id == task.id)
        .order_by(TaskActivity.created_at.desc())
        .limit(30)
    ).all()
    owner_email = db.scalar(select(User.email).where(User.id == task.user_id))
    result = {column.name: getattr(task, column.name) for column in LocalTask.__table__.columns}
    result.update(
        {
            "is_owner": task.user_id == viewer.id,
            "owner_email": owner_email,
            "viewer_participant_id": next(
                (row.id for row, member in participant_rows if member.id == viewer.id), None
            ),
            "participants": [
                {"id": row.id, "user_id": member.id, "email": member.email}
                for row, member in participant_rows
            ],
            "checklist": [
                {
                    "id": item.id,
                    "text": item.text,
                    "completed": item.completed,
                    "position": item.position,
                }
                for item in checklist
            ],
            "activity": [
                {
                    "id": row.id,
                    "actor_email": email,
                    "action": row.action,
                    "details": row.details_json,
                    "created_at": row.created_at,
                }
                for row, email in activities
            ],
        }
    )
    return result
