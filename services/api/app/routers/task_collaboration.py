from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..audit import audit
from ..database import get_db
from ..dependencies import current_user
from ..models import TaskChecklistItem, TaskParticipant, User
from ..schemas import TaskChecklistCreate, TaskChecklistUpdate, TaskParticipantCreate
from ..task_collaboration import accessible_task, add_activity, owner_task, task_view

router = APIRouter(prefix="/api/v1/tasks", tags=["task-collaboration"])


@router.post("/{task_id}/participants", status_code=201)
def add_participant(
    task_id: str,
    body: TaskParticipantCreate,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    task = owner_task(db, task_id, user)
    member = db.scalar(select(User).where(func.lower(User.email) == str(body.email).lower()))
    if not member or member.id == user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    db.add(TaskParticipant(task_id=task.id, user_id=member.id, added_by_user_id=user.id))
    add_activity(db, task, user, "participant_added", {"email": member.email})
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "User already participates") from exc
    audit(db, user, request, "task.participant_added", "task", task.id)
    db.commit()
    return task_view(db, task, user)


@router.delete("/{task_id}/participants/{participant_id}")
def remove_participant(
    task_id: str,
    participant_id: str,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    task = accessible_task(db, task_id, user)
    row = db.get(TaskParticipant, participant_id)
    if not row or row.task_id != task.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Participant not found")
    if task.user_id != user.id and row.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Participant not found")
    removed = db.get(User, row.user_id)
    add_activity(db, task, user, "participant_removed", {"email": removed.email})
    db.delete(row)
    audit(db, user, request, "task.participant_removed", "task", task.id)
    db.commit()
    return task_view(db, task, user)


@router.post("/{task_id}/checklist", status_code=201)
def add_checklist_item(
    task_id: str,
    body: TaskChecklistCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    task = accessible_task(db, task_id, user)
    last = db.scalar(
        select(func.max(TaskChecklistItem.position)).where(TaskChecklistItem.task_id == task.id)
    )
    item = TaskChecklistItem(
        task_id=task.id,
        text=body.text.strip(),
        position=(last or 0) + 1,
        created_by_user_id=user.id,
        updated_by_user_id=user.id,
    )
    db.add(item)
    add_activity(db, task, user, "checklist_added", {"text": item.text})
    db.commit()
    return task_view(db, task, user)


@router.put("/{task_id}/checklist/{item_id}")
def update_checklist_item(
    task_id: str,
    item_id: str,
    body: TaskChecklistUpdate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    task = accessible_task(db, task_id, user)
    item = db.get(TaskChecklistItem, item_id)
    if not item or item.task_id != task.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Checklist item not found")
    changes = body.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(item, field, value.strip() if isinstance(value, str) else value)
    item.updated_by_user_id = user.id
    item.updated_at = datetime.now(UTC)
    add_activity(db, task, user, "checklist_updated", {"fields": sorted(changes)})
    db.commit()
    return task_view(db, task, user)


@router.delete("/{task_id}/checklist/{item_id}", status_code=204)
def delete_checklist_item(
    task_id: str,
    item_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    task = accessible_task(db, task_id, user)
    item = db.get(TaskChecklistItem, item_id)
    if not item or item.task_id != task.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Checklist item not found")
    add_activity(db, task, user, "checklist_deleted", {"text": item.text})
    db.delete(item)
    db.commit()
    return Response(status_code=204)
