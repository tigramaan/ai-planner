import json

import pytest
from sqlalchemy import select

from app import agent, mail_queries
from app.config import get_settings
from app.database import SessionLocal
from app.models import Integration, LocalTask, PendingAction, Reminder, Timer, User
from app.policy import create_pending_action
from app.routers import chat as chat_router
from app.schemas import Intent
from app.security import decrypt_json


@pytest.mark.anyio
async def test_intent_extraction_includes_bounded_conversation_context(monkeypatch):
    captured = {}

    class Responses:
        async def create(self, **kwargs):
            captured.update(kwargs)
            return type(
                "Response",
                (),
                {
                    "output_text": json.dumps(
                        {
                            "intent": "create_meeting",
                            "title": "Teams meeting",
                            "start_iso": "2026-08-03T11:25:00+03:00",
                            "timezone": "Europe/Moscow",
                            "duration_minutes": 30,
                            "participants": ["sorokina@example.com"],
                            "provider": "microsoft",
                            "body": None,
                            "requires_clarification": False,
                            "clarification_question": None,
                        }
                    )
                },
            )()

    class Client:
        def __init__(self, **kwargs):
            self.responses = Responses()

    monkeypatch.setattr(agent, "AsyncOpenAI", Client)
    intent = await agent.extract_intent(
        "test-key",
        "test-model",
        "Москва, sorokina@example.com",
        "ru",
        "Europe/Moscow",
        [
            {"role": "user", "text": "Поставь встречу в Teams сегодня в 11:25"},
            {"role": "assistant", "text": "Укажите email и таймзону"},
        ],
    )
    sent = json.loads(captured["input"])
    assert sent["conversation_history"][0]["role"] == "user"
    assert sent["current_user_message"] == "Москва, sorokina@example.com"
    assert captured["reasoning"] == {"effort": "low"}
    assert intent.intent == "create_meeting"
    assert intent.participants == ["sorokina@example.com"]


@pytest.mark.anyio
async def test_email_summary_is_not_stored_by_openai(monkeypatch):
    captured = {}

    class Responses:
        async def create(self, **kwargs):
            captured.update(kwargs)
            return type("Response", (), {"output_text": "Краткое резюме"})()

    class Client:
        def __init__(self, **kwargs):
            self.responses = Responses()

    monkeypatch.setattr(agent, "AsyncOpenAI", Client)
    result = await agent.summarize_email_content(
        "test-key", "test-model", "low", "Содержание письма", "ru"
    )

    assert result == "Краткое резюме"
    assert captured["store"] is False
    assert captured["reasoning"] == {"effort": "low"}
    assert "untrusted data" in captured["instructions"]


@pytest.mark.anyio
async def test_email_triage_is_bounded_structured_and_not_stored(monkeypatch):
    captured = {}

    class Responses:
        async def create(self, **kwargs):
            captured.update(kwargs)
            items = [
                {
                    "index": index,
                    "category": "ignore",
                    "reason": "Рассылка",
                    "suggested_action": "",
                }
                for index in range(20)
            ]
            return type("Response", (), {"output_text": json.dumps({"items": items})})()

    class Client:
        def __init__(self, **kwargs):
            self.responses = Responses()

    monkeypatch.setattr(agent, "AsyncOpenAI", Client)
    result = await agent.triage_email_rows(
        "test-key",
        "test-model",
        "low",
        [
            {"from": "sender@example.com", "subject": f"Subject {index}", "snippet": "x" * 2000}
            for index in range(25)
        ],
        "ru",
    )

    assert len(result) == 20
    assert captured["store"] is False
    assert captured["reasoning"] == {"effort": "low"}
    assert len(json.loads(captured["input"])) == 20
    assert len(json.loads(captured["input"])[0]["snippet"]) == 1200
    assert "untrusted data" in captured["instructions"]
    assert "every automated message" in captured["instructions"]
    assert captured["text"]["format"]["type"] == "json_schema"


@pytest.mark.anyio
async def test_intent_schema_delegates_mail_strategy_to_model(monkeypatch):
    captured = {}

    class Responses:
        async def create(self, **kwargs):
            captured.update(kwargs)
            payload = {key: None for key in Intent.model_json_schema()["properties"]}
            payload.update(
                intent="search_email",
                mail_mode="triage",
                mail_limit=3,
                participants=[],
                conference_requested=False,
                requires_senior=False,
                requires_clarification=False,
            )
            return type("Response", (), {"output_text": json.dumps(payload)})()

    class Client:
        def __init__(self, **kwargs):
            self.responses = Responses()

    monkeypatch.setattr(agent, "AsyncOpenAI", Client)
    intent = await agent.extract_intent(
        "key",
        "model",
        "Разбери входящие и оставь то, что заслуживает моего времени",
        "ru",
    )

    assert intent.mail_mode == "triage"
    assert intent.mail_limit == 3
    assert "choose mail_mode semantically" in captured["instructions"]
    assert "mail_mode" in captured["text"]["format"]["schema"]["required"]

def test_mail_access_requires_incremental_scope(logged_in):
    with SessionLocal() as db:
        user = db.scalar(select(User))
        integration = Integration(
            user_id=user.id, provider="google", status="connected", scopes=["openid"]
        )
        db.add(integration)
        db.commit()
        assert not mail_queries.mail_access_granted(db, user, "google")
        integration.scopes = ["https://www.googleapis.com/auth/gmail.readonly"]
        db.commit()
        assert mail_queries.mail_access_granted(db, user, "google")


def test_mail_send_requires_compose_or_send_scope(logged_in):
    with SessionLocal() as db:
        user = db.scalar(select(User))
        integration = Integration(
            user_id=user.id,
            provider="google",
            status="connected",
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
        )
        db.add(integration)
        db.commit()
        assert not chat_router.mail_send_access_granted(db, user, "google")
        integration.scopes = [*integration.scopes, "https://www.googleapis.com/auth/gmail.send"]
        db.commit()
        assert chat_router.mail_send_access_granted(db, user, "google")


def test_email_draft_shows_exact_text_and_requires_confirmation(logged_in, monkeypatch):
    async def intent(*args, **kwargs):
        return Intent(
            intent="send_email",
            title="Итоги проекта",
            body="Добрый день! Подтвердите, пожалуйста, итоговую стоимость проекта.",
            participants=["recipient@example.com"],
            provider="google",
        )

    monkeypatch.setattr(chat_router, "extract_intent", intent)
    with SessionLocal() as db:
        user = db.scalar(select(User))
        db.add(
            Integration(
                user_id=user.id,
                provider="google",
                status="connected",
                scopes=["https://www.googleapis.com/auth/gmail.send"],
            )
        )
        db.commit()

    response = logged_in.post(
        "/api/v1/chat/messages",
        json={"text": "Напиши вежливое письмо с просьбой подтвердить стоимость"},
    )
    assert response.status_code == 200
    assert response.json()["pending_action_id"] is not None
    assert "Итоги проекта" in response.json()["message"]
    assert "recipient@example.com" in response.json()["message"]
    assert "Подтвердите, пожалуйста" in response.json()["message"]


def test_complex_command_is_escalated_to_senior_model(logged_in, monkeypatch):
    calls = []

    async def intent(api_key, model, text, locale, timezone, history, reasoning_effort):
        calls.append((model, reasoning_effort))
        if len(calls) == 1:
            return Intent(
                intent="show_today",
                requires_senior=True,
                route_reason="Several dependent operations",
            )
        return Intent(intent="show_today")

    monkeypatch.setattr(chat_router, "extract_intent", intent)
    response = logged_in.post(
        "/api/v1/chat/messages",
        json={"text": "Разбери входящие, подготовь ответы и поставь задачи по срокам"},
    )

    assert response.status_code == 200
    assert calls == [("gpt-5.6-luna", "low"), ("gpt-5.6-sol", "medium")]


def test_simple_command_stays_on_junior_model(logged_in, monkeypatch):
    calls = []

    async def intent(api_key, model, text, locale, timezone, history, reasoning_effort):
        calls.append((model, reasoning_effort))
        return Intent(intent="show_today")

    monkeypatch.setattr(chat_router, "extract_intent", intent)
    response = logged_in.post("/api/v1/chat/messages", json={"text": "Что сегодня?"})

    assert response.status_code == 200
    assert calls == [("gpt-5.6-luna", "low")]


def test_task_can_be_created_with_details_and_completed_through_chat(logged_in, monkeypatch):
    responses = iter(
        [
            Intent(
                intent="create_task",
                title="Подготовить договор",
                body="Проверить приложение",
                start_iso="2026-08-05T18:00:00+03:00",
                timezone="Europe/Moscow",
                priority="high",
            ),
            Intent(
                intent="complete_task",
                event_query="Подготовить договор",
            ),
            Intent(
                intent="reopen_task",
                event_query="Подготовить договор",
            ),
        ]
    )

    async def intent(*args, **kwargs):
        return next(responses)

    monkeypatch.setattr(chat_router, "extract_intent", intent)
    created = logged_in.post("/api/v1/chat/messages", json={"text": "Создай задачу"})
    assert created.status_code == 200
    assert "Enable notifications" in created.json()["message"]
    assert logged_in.post("/api/v1/chat/messages", json={"text": "Задача сделана"}).status_code == 200
    reopened = logged_in.post("/api/v1/chat/messages", json={"text": "Верни задачу в работу"})
    assert reopened.status_code == 200
    with SessionLocal() as db:
        task = db.scalar(select(LocalTask).where(LocalTask.title == "Подготовить договор"))
        assert task.status == "open"
        assert task.priority == "high"
        assert task.description == "Проверить приложение"
        assert task.due_at is not None
        assert db.scalar(select(Reminder).where(Reminder.task_id == task.id)) is not None


def test_timer_can_be_restarted_and_deleted_through_chat(logged_in, monkeypatch):
    with SessionLocal() as db:
        user = db.scalar(select(User))
        db.add(Timer(user_id=user.id, title="Фокус", ends_at=user.created_at))
        db.commit()
    responses = iter(
        [
            Intent(intent="update_timer", event_query="Фокус", duration_minutes=10),
            Intent(intent="cancel_timer", event_query="Фокус"),
        ]
    )

    async def intent(*args, **kwargs):
        return next(responses)

    monkeypatch.setattr(chat_router, "extract_intent", intent)
    restarted = logged_in.post("/api/v1/chat/messages", json={"text": "Перезапусти Фокус"})
    assert "10 minutes" in restarted.json()["message"]
    assert "Enable push notifications" in restarted.json()["message"]
    with SessionLocal() as db:
        timer = db.scalar(select(Timer).where(Timer.title == "Фокус"))
        reminder = db.scalar(select(Reminder).where(Reminder.timer_id == timer.id))
        assert reminder is not None
    deleted = logged_in.post("/api/v1/chat/messages", json={"text": "Удали Фокус"})
    assert "deleted" in deleted.json()["message"]


def test_correction_replaces_pending_draft(logged_in, monkeypatch):
    async def intent(*args, **kwargs):
        text = args[2]
        hour = 16 if "16:00" in text else 15
        return Intent(
            intent="create_meeting",
            title="Встреча с Анастасией",
            start_iso=f"2026-08-04T{hour:02d}:00:00+03:00",
            timezone="Europe/Moscow",
            participants=["anastasia@example.com"],
            provider="microsoft",
        )

    async def recipients(*args, **kwargs):
        return type("Resolution", (), {"recipients": args[3], "ambiguous": {}, "unresolved": []})()

    monkeypatch.setattr(chat_router, "extract_intent", intent)
    monkeypatch.setattr(chat_router, "resolve_recipients", recipients)
    first = logged_in.post("/api/v1/chat/messages", json={"text": "Встреча завтра в 15:00"})
    second = logged_in.post("/api/v1/chat/messages", json={"text": "Нет, перенеси на 16:00"})
    assert first.status_code == second.status_code == 200
    assert "16:00" in second.json()["message"]
    with SessionLocal() as db:
        rows = db.scalars(select(PendingAction).order_by(PendingAction.expires_at)).all()
        assert len(rows) == 2
        assert rows[0].cancelled_at is not None
        assert rows[1].cancelled_at is None


def test_explicit_correction_recovers_cancelled_unexecuted_draft(logged_in):
    with SessionLocal() as db:
        user = db.scalar(select(User))
        action = create_pending_action(
            db,
            get_settings(),
            user,
            "create_meeting",
            "Встреча 03.08.2026 в 11:25 Europe/Moscow",
            {
                "title": "Встреча с Анастасией",
                "start_iso": "2026-08-03T08:25:00+00:00",
                "end_iso": "2026-08-03T08:55:00+00:00",
                "timezone": "Europe/Moscow",
                "attendees": ["anastasia@example.com"],
                "provider": "microsoft",
                "conference": "microsoft_teams",
            },
        )
        action.cancelled_at = action.expires_at
        db.commit()
        context = chat_router.cancelled_draft_context(
            db, get_settings(), user, "Измени время этой встречи на 12:30"
        )
        assert context is not None
        assert "not executed" in context["text"]
        assert "create_meeting" in context["text"]
        assert "anastasia@example.com" in context["text"]
        assert (
            chat_router.cancelled_draft_context(
                db, get_settings(), user, "Создай новую задачу"
            )
            is None
        )


def test_current_telemost_request_overrides_stale_teams_intent(logged_in, monkeypatch):
    async def stale_teams_intent(*args, **kwargs):
        return Intent(
            intent="create_meeting",
            title="Встреча",
            start_iso="2026-08-03T15:30:00+03:00",
            timezone="Europe/Moscow",
            provider="google",
            conference_provider="microsoft",
            conference_requested=True,
        )

    monkeypatch.setattr(chat_router, "extract_intent", stale_teams_intent)
    response = logged_in.post(
        "/api/v1/chat/messages", json={"text": "Время 15:30 и встреча в Телемосте"}
    )
    assert response.status_code == 200
    assert "Video service: Яндекс Телемост" in response.json()["message"]
    with SessionLocal() as db:
        action = db.scalar(select(PendingAction).order_by(PendingAction.expires_at.desc()))
        payload = decrypt_json(
            get_settings(),
            action.payload_encrypted,
            f"pending:{action.id}:{action.payload_hash}",
        )
        assert payload["conference"] == "yandex_telemost"
        assert payload["reminder_minutes"] == 5


def test_current_telemost_request_overrides_video_on_event_update(logged_in, monkeypatch):
    async def updated_event(*args, **kwargs):
        return Intent(
            intent="update_event",
            event_query="Встреча с Анастасией",
            event_start_iso="2026-08-03T15:30:00+03:00",
            start_iso="2026-08-03T16:30:00+03:00",
            timezone="Europe/Moscow",
            provider="google",
            conference_provider="microsoft",
            conference_requested=True,
        )

    async def prepared(*args, **kwargs):
        intent = args[-1]
        return {
            "schema_version": 1,
            "provider": "google",
            "event_id": "event-1",
            "event_title": "Встреча с Анастасией",
            "start_iso": "2026-08-03T13:30:00+00:00",
            "end_iso": "2026-08-03T14:00:00+00:00",
            "timezone": "Europe/Moscow",
            "conference": "yandex_telemost" if intent.conference_provider == "yandex" else "none",
        }, "updated"

    monkeypatch.setattr(chat_router, "extract_intent", updated_event)
    monkeypatch.setattr(chat_router, "prepare_calendar_action", prepared)
    response = logged_in.post(
        "/api/v1/chat/messages",
        json={"text": "Перенеси на 16:30 и сделай видеовстречу в Яндекс Телемосте"},
    )
    assert response.status_code == 200
    assert "Video service: Яндекс Телемост" in response.json()["message"]


def test_ambiguous_calendar_match_offers_numbered_choices(logged_in, monkeypatch):
    async def intent(*args, **kwargs):
        return Intent(
            intent="update_event",
            event_query="с Анастасией",
            start_iso="2026-08-03T18:00:00+03:00",
            provider="google",
        )

    async def ambiguous(*args, **kwargs):
        raise chat_router.EventAmbiguous(
            [
                "Встреча с Анастасией Сорокиной (03.08.2026, 15:30)",
                "Созвон с Анастасией (04.08.2026, 11:00)",
            ]
        )

    monkeypatch.setattr(chat_router, "extract_intent", intent)
    monkeypatch.setattr(chat_router, "prepare_calendar_action", ambiguous)
    response = logged_in.post(
        "/api/v1/chat/messages",
        json={"text": "Перенеси встречу с Анастасией на 18:00"},
        headers={"accept-language": "ru"},
    )
    assert response.status_code == 200
    assert "1. Встреча с Анастасией" in response.json()["message"]
    assert "2. Созвон с Анастасией" in response.json()["message"]
    assert "Ответьте номером" in response.json()["message"]
