from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..adapters import ProviderError, search_email
from ..agenda import collect_agenda
from ..agent import openai_config
from ..audit import audit
from ..commitments import analyze_commitments
from ..config import Settings, get_settings
from ..database import get_db
from ..dependencies import current_user
from ..integrations import valid_access_token
from ..mail_queries import MAIL_READ_SCOPE, mail_access_granted
from ..models import LocalTask, User

router = APIRouter(prefix="/api/v1/commitments", tags=["commitments"])


@router.post("/analyze")
async def commitment_radar(
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    provider = user.default_mail
    if provider not in MAIL_READ_SCOPE or not mail_access_granted(db, user, provider):
        raise HTTPException(409, "Сначала подключите чтение почты в настройках")
    try:
        token = await valid_access_token(db, settings, user, provider)
        if provider == "google":
            incoming_query, sent_query = "newer_than:30d -in:sent", "in:sent newer_than:30d"
        else:
            incoming_query, sent_query = "received", "sent"
        incoming = await search_email(provider, token, incoming_query, limit=15)
        sent = await search_email(provider, token, sent_query, limit=15)
        _, _, agenda = await collect_agenda(db, settings, user, 30)
    except LookupError as exc:
        raise HTTPException(409, "Переподключите почту в настройках") from exc
    except ProviderError as exc:
        raise HTTPException(502, f"Почтовый сервис отклонил запрос ({exc.status_code})") from exc
    tasks = db.scalars(
        select(LocalTask).where(LocalTask.user_id == user.id, LocalTask.status == "open")
    ).all()
    config = openai_config(db, settings, user)
    try:
        items = await analyze_commitments(
            config["api_key"], config["model"], config["reasoning_effort"],
            incoming, sent,
            [{"title": row.title, "due_at": row.due_at} for row in tasks],
            agenda, user.locale,
        )
    except RuntimeError as exc:
        raise HTTPException(503, "Сейчас не удалось надёжно проверить обязательства") from exc
    audit(
        db, user, request, "commitments.analyzed", "user", user.id,
        {"incoming_checked": len(incoming), "sent_checked": len(sent), "items": len(items)},
    )
    db.commit()
    return {"window_days": 30, "items": items}
