import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..audit import audit
from ..config import Settings, get_settings
from ..database import get_db
from ..dependencies import current_user
from ..models import FamilyInvite, User
from ..schemas import FamilyInviteView
from ..security import token_hash

router = APIRouter(prefix="/api/v1/family", tags=["family"])


@router.post("/invites", response_model=FamilyInviteView, status_code=201)
def create_invite(
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only an administrator can invite members")
    raw = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC) + timedelta(days=7)
    invite = FamilyInvite(
        created_by_user_id=user.id,
        token_hash=token_hash(raw),
        expires_at=expires_at,
    )
    db.add(invite)
    db.flush()
    audit(db, user, request, "family.invite_created", "family_invite", invite.id)
    db.commit()
    return {
        "invite_url": f"{settings.public_base_url}/register?invite={raw}",
        "expires_at": expires_at,
    }
