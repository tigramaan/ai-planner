import re
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..action_summary import action_summary
from ..adapters import ProviderError
from ..agent import (
    extract_intent,
    openai_config,
    pending_payload,
    risk_for_intent,
    transcribe,
)
from ..audit import audit
from ..calendar_actions import EventAmbiguous, EventNotFound, prepare_calendar_action
from ..conference_intent import explicit_conference_provider
from ..config import Settings, get_settings
from ..database import get_db
from ..dependencies import current_user
from ..local_chat_actions import LOCAL_INTENTS, handle_local_intent
from ..mail_chat import handle_mail_search
from ..mail_queries import mail_send_access_granted
from ..models import AgentMessage, PendingAction, Reminder, User
from ..policy import action_status, create_pending_action
from ..recipient_aliases import remembered_recipient_request, save_recipient_alias
from ..recipients import resolve_recipients
from ..schemas import ChatRequest
from ..security import decrypt_json

router = APIRouter(prefix="/api/v1", tags=["agent"])
AFFIRMATIVE = {
    "да",
    "давай",
    "подтверждаю",
    "подтвердить",
    "выполняй",
    "выполни",
    "yes",
    "confirm",
    "go ahead",
    "do it",
}
NEGATIVE = {"нет", "не надо", "отмена", "отмени", "cancel", "no"}


def decision(text: str) -> str | None:
    normalized = re.sub(r"[^\w\s]", "", text.casefold()).strip()
    if normalized in AFFIRMATIVE:
        return "confirm"
    if normalized in NEGATIVE:
        return "cancel"
    return None


def pending_drafts(db: Session, user: User) -> list[PendingAction]:
    rows = db.scalars(
        select(PendingAction)
        .where(PendingAction.user_id == user.id)
        .order_by(PendingAction.expires_at.desc())
        .limit(10)
    ).all()
    return [row for row in rows if action_status(row) == "pending"]


def references_recent_draft(text: str) -> bool:
    normalized = text.casefold()
    references = ("эту", "этой", "чернов", "предыдущ", "встреч", "it", "this", "draft", "previous")
    changes = (
        "измени",
        "поменя",
        "перенес",
        "добав",
        "ещё",
        "еще",
        "correct",
        "change",
        "move",
        "add",
    )
    return any(value in normalized for value in references) and any(
        value in normalized for value in changes
    )


def cancelled_draft_context(
    db: Session, settings: Settings, user: User, text: str
) -> dict[str, str] | None:
    if not references_recent_draft(text):
        return None
    rows = db.scalars(
        select(PendingAction)
        .where(PendingAction.user_id == user.id, PendingAction.cancelled_at.is_not(None))
        .order_by(PendingAction.cancelled_at.desc())
        .limit(1)
    ).all()
    if not rows:
        return None
    action = rows[0]
    payload = decrypt_json(
        settings, action.payload_encrypted, f"pending:{action.id}:{action.payload_hash}"
    )
    safe = {
        key: payload.get(key)
        for key in (
            "title",
            "start_iso",
            "end_iso",
            "timezone",
            "attendees",
            "provider",
            "conference",
        )
        if payload.get(key) is not None
    }
    return {
        "role": "assistant",
        "text": (
            f"Recently cancelled, not executed draft. Action type: {action.action_type}. "
            f"Summary: {action.display_summary}. Structured draft: {safe}"
        )[:2000],
    }


def browser_locale(request: Request) -> str:
    languages = request.headers.get("accept-language", "").lower().split(",")
    for language in languages:
        primary = language.strip().split(";")[0].split("-")[0]
        if primary in {"ru", "en"}:
            return primary
    return "en"


@router.get("/chat/messages")
def messages(user: User = Depends(current_user), db: Session = Depends(get_db)):
    latest = db.scalars(
        select(AgentMessage)
        .where(AgentMessage.user_id == user.id)
        .order_by(AgentMessage.created_at.desc())
        .limit(50)
    ).all()
    return list(reversed(latest))


@router.post("/chat/messages")
async def chat(
    body: ChatRequest,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    locale = browser_locale(request)
    ru = locale == "ru"
    drafts = pending_drafts(db, user)
    active_pending = drafts[0] if drafts else None
    requested_decision = decision(body.text)
    if active_pending and requested_decision:
        from .planner import cancel as cancel_pending
        from .planner import confirm as confirm_pending

        user_message = AgentMessage(user_id=user.id, role="user", text=body.text)
        db.add(user_message)
        if requested_decision == "confirm":
            for stale in drafts[1:]:
                stale.cancelled_at = datetime.now(UTC)
            result = await confirm_pending(active_pending.id, request, user, db, settings)
            execution = result.get("result") or {}
            answer = execution.get("report") or (
                "Действие выполнено." if ru else "Action completed."
            )
        else:
            cancel_pending(active_pending.id, request, user, db)
            answer = "Черновик отменён." if ru else "Draft cancelled."
        return {"intent": None, "message": answer, "pending_action_id": None}
    config = openai_config(db, settings, user)
    recent = db.scalars(
        select(AgentMessage)
        .where(AgentMessage.user_id == user.id)
        .order_by(AgentMessage.created_at.desc())
        .limit(8)
    ).all()
    remembered = remembered_recipient_request(body.text, recent)
    history = [{"role": row.role, "text": row.text[:2000]} for row in reversed(recent)]
    cancelled_context = cancelled_draft_context(db, settings, user, body.text)
    if cancelled_context:
        history.append(cancelled_context)
    try:
        intent = await extract_intent(
            config["api_key"],
            config["model"],
            body.text,
            locale,
            user.timezone,
            history,
            config["reasoning_effort"],
        )
    except RuntimeError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    explicit_conference = explicit_conference_provider(body.text)
    if intent.intent in {"create_meeting", "update_event"} and explicit_conference:
        intent.conference_requested = True
        intent.conference_provider = explicit_conference
    if intent.intent in {
        "create_meeting",
        "update_event",
        "cancel_event",
        "add_event_participants",
    }:
        intent.provider = intent.provider or user.default_calendar
    if intent.intent in {"send_email", "search_email"}:
        intent.provider = intent.provider or user.default_mail
    if intent.intent == "create_meeting":
        intent.conference_provider = (
            intent.conference_provider or user.default_conference
            if intent.conference_requested
            else "none"
        )
    user_message = AgentMessage(
        user_id=user.id, role="user", text=body.text, structured_intent_json=intent.model_dump()
    )
    db.add(user_message)
    if remembered:
        save_recipient_alias(db, settings, user, *remembered)
    pending = None
    intent.timezone = intent.timezone or user.timezone
    if intent.intent == "create_meeting" and not intent.title:
        participant_names = ", ".join(intent.participants)
        if ru:
            intent.title = f"Встреча с {participant_names}" if participant_names else "Встреча"
        else:
            intent.title = f"Meeting with {participant_names}" if participant_names else "Meeting"
    resolution_answer = None
    if (
        intent.intent in {"create_meeting", "add_event_participants", "send_email"}
        and intent.participants
    ):
        provider = (
            intent.provider
            if intent.provider in {"google", "microsoft", "yandex"}
            else user.default_calendar
        )
        resolution = await resolve_recipients(db, settings, user, intent.participants, provider)
        intent.participants = resolution.recipients
        if resolution.ambiguous:
            choices = "; ".join(
                f"{name}: {', '.join(addresses)}"
                for name, addresses in resolution.ambiguous.items()
            )
            resolution_answer = (
                f"Нашёл несколько адресов. Уточните нужный: {choices}"
                if ru
                else f"I found multiple addresses. Choose one: {choices}"
            )
        elif resolution.unresolved:
            names = ", ".join(resolution.unresolved)
            resolution_answer = (
                f"Не нашёл адрес для: {names}. Укажите email или добавьте контакт."
                if ru
                else f"No address found for: {names}. Provide an email or add the contact."
            )
    if (
        intent.intent == "send_email"
        and not resolution_answer
        and not mail_send_access_granted(db, user, intent.provider or user.default_mail)
    ):
        resolution_answer = (
            "Для отправки письма нужно разрешение Gmail. Откройте «Настройки», "
            "нажмите «Авторизовать Gmail» и разрешите создание и отправку писем."
            if ru
            else "Email sending is not authorized. Open Settings, authorize Gmail, "
            "and allow composing and sending email."
        )
    prepared_payload = None
    prepared_summary = None
    action_error = None
    calendar_actions = {"update_event", "cancel_event", "add_event_participants"}
    if (
        intent.intent in calendar_actions
        and not resolution_answer
        and not intent.requires_clarification
    ):
        try:
            prepared_payload, prepared_summary = await prepare_calendar_action(
                db, settings, user, intent
            )
        except EventNotFound as exc:
            if exc.choices:
                options = "; ".join(f"{index}. {choice}" for index, choice in enumerate(exc.choices, 1))
                action_error = (
                    f"Не нашёл точного совпадения. Возможно, вы имели в виду: {options}. Ответьте номером."
                    if ru
                    else f"No close match found. Did you mean: {options}. Reply with a number."
                )
            else:
                action_error = (
                    "Не нашёл событий в календаре за ближайший период."
                    if ru
                    else "No calendar events were found in the nearby date range."
                )
        except EventAmbiguous as exc:
            options = "; ".join(f"{index}. {choice}" for index, choice in enumerate(exc.choices, 1))
            action_error = (
                f"Нашёл несколько подходящих событий: {options}. Ответьте номером."
                if ru
                else f"I found several matching events: {options}. Reply with a number."
            )
        except LookupError:
            action_error = (
                "Сначала подключите нужный календарь в настройках."
                if ru
                else "Connect the required calendar in Settings first."
            )
        except ValueError as exc:
            action_error = str(exc)
        except ProviderError as exc:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    if resolution_answer:
        answer = resolution_answer
    elif action_error:
        answer = action_error
    elif intent.requires_clarification:
        answer = intent.clarification_question or (
            "Уточните параметры команды." if ru else "Please clarify the command parameters."
        )
    elif risk_for_intent(intent) == "confirmation_required":
        try:
            payload = prepared_payload or pending_payload(intent)
            if intent.intent == "create_meeting":
                payload["reminder_minutes"] = user.default_reminder_minutes
        except (ValueError, TypeError) as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
        summary = action_summary(intent.intent, payload, locale)
        if prepared_summary and not summary:
            summary = prepared_summary
        for draft in drafts:
            draft.cancelled_at = datetime.now(UTC)
        pending = create_pending_action(db, settings, user, intent.intent, summary, payload)
        answer = summary + (
            "\nЕсли всё верно, ответьте «Подтверждаю» или нажмите кнопку. Чтобы исправить, напишите изменение."
            if ru
            else "\nIf this is correct, reply “Confirm” or press the button. To revise it, send the correction."
        )
    elif intent.intent in LOCAL_INTENTS:
        answer = handle_local_intent(db, user, intent, body.text, ru)
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
        answer = (
            f"Напоминание «{reminder.title}» запланировано."
            if ru
            else f'Reminder "{reminder.title}" scheduled.'
        )
    elif intent.intent == "show_today":
        answer = (
            "Откройте экран «Сегодня»: данные уже обновляются из подключённых источников."
            if ru
            else "Open Today. Data is already updating from connected sources."
        )
    elif intent.intent == "search_email":
        answer = await handle_mail_search(db, settings, user, intent, body.text, config, locale)
    else:
        answer = (
            "Я понял команду, но для этого действия пока нет безопасного инструмента."
            if ru
            else "I understood the command, but no safe tool is available for this action yet."
        )
    assistant = AgentMessage(user_id=user.id, role="assistant", text=answer)
    if remembered:
        name, email = remembered
        notice = (
            f"\nКонтакт «{name}» сохранён для будущих запросов: {email}."
            if ru
            else f"\nSaved {name} for future requests: {email}."
        )
        answer += notice
        assistant.text = answer
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
    content_type = (audio.content_type or "").split(";", 1)[0].strip().lower()
    if content_type not in {
        "audio/webm",
        "audio/ogg",
        "audio/mpeg",
        "audio/mp4",
        "audio/x-m4a",
        "audio/wav",
        "video/mp4",
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
