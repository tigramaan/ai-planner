from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..adapters import ProviderError, search_email
from ..agent import extract_intent, openai_config, pending_payload, risk_for_intent, transcribe
from ..audit import audit
from ..config import Settings, get_settings
from ..database import get_db
from ..dependencies import current_user
from ..integrations import valid_access_token
from ..models import AgentMessage, LocalTask, Reminder, Timer, User
from ..policy import create_pending_action
from ..schemas import ChatRequest

router = APIRouter(prefix="/api/v1", tags=["agent"])


@router.get("/chat/messages")
def messages(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return db.scalars(
        select(AgentMessage)
        .where(AgentMessage.user_id == user.id)
        .order_by(AgentMessage.created_at)
        .limit(200)
    ).all()


@router.post("/chat/messages")
async def chat(
    body: ChatRequest,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    config = openai_config(db, settings, user)
    try:
        intent = await extract_intent(config["api_key"], config["model"], body.text)
    except RuntimeError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    user_message = AgentMessage(
        user_id=user.id, role="user", text=body.text, structured_intent_json=intent.model_dump()
    )
    db.add(user_message)
    pending = None
    if intent.requires_clarification:
        answer = intent.clarification_question or "Уточните параметры команды."
    elif risk_for_intent(intent) == "confirmation_required":
        summary = f"{intent.title or intent.intent}. Проверьте участников, дату и время перед выполнением."
        try:
            payload = pending_payload(intent)
        except (ValueError, TypeError) as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
        pending = create_pending_action(db, settings, user, intent.intent, summary, payload)
        answer = "Подготовил действие. Выполню только после вашего подтверждения."
    elif intent.intent == "create_task":
        task = LocalTask(
            user_id=user.id,
            title=intent.title or body.text,
            timezone=intent.timezone or user.timezone,
        )
        db.add(task)
        answer = f"Задача «{task.title}» создана."
    elif intent.intent == "create_reminder":
        if not intent.start_iso or not intent.timezone:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Reminder requires time and timezone",
            )
        due_at = datetime.fromisoformat(intent.start_iso)
        if due_at.tzinfo is None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Reminder time requires UTC offset",
            )
        reminder = Reminder(
            user_id=user.id,
            title=intent.title or body.text,
            due_at=due_at,
            next_attempt_at=due_at,
            timezone=intent.timezone,
        )
        db.add(reminder)
        answer = f"Напоминание «{reminder.title}» запланировано."
    elif intent.intent == "start_timer":
        seconds = (intent.duration_minutes or 25) * 60
        timer = Timer(
            user_id=user.id,
            title=intent.title or "Таймер",
            ends_at=datetime.now().astimezone() + timedelta(seconds=seconds),
        )
        db.add(timer)
        answer = f"Таймер запущен на {seconds // 60} минут."
    elif intent.intent == "show_today":
        answer = "Откройте экран «Сегодня»: данные уже обновляются из подключённых источников."
    elif intent.intent == "search_email":
        provider = intent.provider if intent.provider in {"google", "microsoft"} else "google"
        try:
            token = await valid_access_token(db, settings, user, provider)
            rows = await search_email(provider, token, intent.body or intent.title or body.text)
        except LookupError:
            answer = f"Сначала подключите {provider} в настройках."
        except ProviderError as exc:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
        else:
            answer = (
                "Писем не найдено."
                if not rows
                else "\n".join(
                    f"{index + 1}. {row['subject']} | {row['from']}"
                    for index, row in enumerate(rows)
                )
            )
    else:
        answer = "Я понял команду, но для этого действия пока нет безопасного инструмента."
    assistant = AgentMessage(user_id=user.id, role="assistant", text=answer)
    db.add(assistant)
    audit(
        db,
        user,
        request,
        "agent.command",
        "message",
        user_message.id,
        {"intent": intent.intent, "pending": bool(pending)},
    )
    db.commit()
    return {
        "intent": intent,
        "message": answer,
        "pending_action_id": pending.id if pending else None,
    }


@router.post("/voice/transcribe")
async def voice(
    request: Request,
    audio: UploadFile = File(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    if audio.content_type not in {
        "audio/webm",
        "audio/ogg",
        "audio/mpeg",
        "audio/mp4",
        "audio/wav",
        "application/octet-stream",
    }:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Unsupported audio type")
    content = await audio.read(25 * 1024 * 1024 + 1)
    if not content or len(content) > 25 * 1024 * 1024:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Audio must be between 1 byte and 25 MB"
        )
    config = openai_config(db, settings, user)
    try:
        text = await transcribe(
            config["api_key"],
            config["transcription_model"],
            audio.filename or "voice.webm",
            content,
        )
    except RuntimeError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    audit(db, user, request, "voice.transcribed", "audio", details={"size": len(content)})
    db.commit()
    return {"text": text}
