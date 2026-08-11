from fastapi import Request
from sqlalchemy.orm import Session

from .audit import audit
from .models import AgentMessage, User


def decision_without_active_draft(
    db: Session,
    user: User,
    request: Request,
    text: str,
    requested_decision: str,
    ru: bool,
) -> dict:
    answer = (
        "Нет активного черновика для подтверждения. Возможно, он уже выполнен или истёк. "
        "Повторите исходную команду, если нужно создать новое действие."
        if ru
        else "There is no active draft to confirm. It may already be executed or expired. "
        "Repeat the original command if you want to create a new action."
    )
    user_message = AgentMessage(user_id=user.id, role="user", text=text)
    db.add(user_message)
    db.add(AgentMessage(user_id=user.id, role="assistant", text=answer))
    audit(
        db,
        user,
        request,
        "pending_action.decision_without_active_draft",
        "message",
        user_message.id,
        {"decision": requested_decision},
    )
    db.commit()
    return {"intent": None, "message": answer, "pending_action_id": None}
