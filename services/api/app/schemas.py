from datetime import datetime
from typing import Any, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, EmailStr, Field, field_validator


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)
    device_name: str = Field(default="browser", max_length=160)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=256)
    registration_code: str | None = Field(default=None, min_length=1, max_length=256)
    invite_token: str | None = Field(default=None, min_length=20, max_length=256)
    device_name: str = Field(default="browser", max_length=160)


class FamilyInviteView(BaseModel):
    invite_url: str
    expires_at: datetime


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=12, max_length=256)


class InitialSetupRequest(BaseModel):
    setup_token: str = Field(min_length=32, max_length=256)
    password: str = Field(min_length=12, max_length=256)
    device_name: str = Field(default="browser", max_length=160)


class UserView(BaseModel):
    id: str
    email: str
    timezone: str
    locale: str
    is_admin: bool


class SecretWrite(BaseModel):
    api_key: str = Field(min_length=10, max_length=500)
    model: str = Field(default="gpt-5.6-luna", max_length=100)
    transcription_model: str = Field(default="whisper-1", max_length=100)


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(default="", max_length=5000)
    due_at: datetime | None = None
    timezone: str = Field(default="Europe/Moscow", max_length=64)
    priority: Literal["low", "normal", "high"] = "normal"


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=5000)
    due_at: datetime | None = None
    timezone: str | None = Field(default=None, max_length=64)
    priority: Literal["low", "normal", "high"] | None = None
    status: Literal["open", "completed"] | None = None

    @field_validator("title", "description", "timezone", "priority", "status")
    @classmethod
    def reject_null_values(cls, value):
        if value is None:
            raise ValueError("Field cannot be null")
        return value


class TimerCreate(BaseModel):
    title: str = Field(default="Таймер", max_length=300)
    duration_seconds: int = Field(ge=1, le=86400)


class TimerUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    duration_seconds: int | None = Field(default=None, ge=1, le=86400)


class ReminderCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    due_at: datetime
    timezone: str = Field(default="Europe/Moscow", max_length=64)
    channel: Literal["push", "in_app"] = "push"


class PushSubscriptionWrite(BaseModel):
    endpoint: str = Field(min_length=20, max_length=2000)
    p256dh: str = Field(min_length=20, max_length=500)
    auth: str = Field(min_length=8, max_length=500)


class ReminderDelivery(BaseModel):
    status: Literal["delivered", "retry", "failed"]
    error: str | None = Field(default=None, max_length=300)


class ChatRequest(BaseModel):
    text: str = Field(min_length=1, max_length=12000)


class UserPreferences(BaseModel):
    default_calendar: Literal["google", "microsoft", "yandex", "local"]
    default_mail: Literal["google", "microsoft", "yandex"]
    default_conference: Literal["none", "google", "microsoft", "yandex", "zoom"]
    default_reminder_minutes: int = Field(default=5, ge=0, le=10080)
    fallback_teams_url: str = Field(default="", max_length=2000)
    fallback_telemost_url: str = Field(default="", max_length=2000)

    @field_validator("fallback_teams_url", "fallback_telemost_url")
    @classmethod
    def safe_fallback_url(cls, value: str, info) -> str:
        value = value.strip()
        if not value:
            return ""
        parsed = urlparse(value)
        allowed = (
            {"teams.microsoft.com", "teams.live.com"}
            if info.field_name == "fallback_teams_url"
            else {"telemost.yandex.ru"}
        )
        if parsed.scheme != "https" or parsed.hostname not in allowed:
            raise ValueError("Fallback URL must be an HTTPS Teams or Yandex Telemost link")
        return value


class Intent(BaseModel):
    intent: Literal[
        "show_today",
        "create_task",
        "update_task",
        "complete_task",
        "reopen_task",
        "delete_task",
        "create_reminder",
        "start_timer",
        "update_timer",
        "cancel_timer",
        "create_meeting",
        "update_event",
        "cancel_event",
        "add_event_participants",
        "send_email",
        "search_email",
        "unknown",
    ]
    title: str | None = None
    event_query: str | None = None
    event_start_iso: str | None = None
    start_iso: str | None = None
    timezone: str | None = None
    duration_minutes: int | None = Field(default=None, ge=1, le=1440)
    priority: Literal["low", "normal", "high"] | None = None
    participants: list[str] = Field(default_factory=list, max_length=50)
    provider: Literal["google", "microsoft", "yandex", "local"] | None = None
    mail_mode: Literal["search", "summarize", "triage"] = "search"
    conference_provider: Literal["google", "microsoft", "yandex", "zoom", "none"] | None = None
    conference_requested: bool = False
    body: str | None = None
    requires_senior: bool = False
    route_reason: str | None = Field(default=None, max_length=300)
    requires_clarification: bool = False
    clarification_question: str | None = None


class OAuthStart(BaseModel):
    scopes: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("scopes")
    @classmethod
    def unique_scopes(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(value))


class PendingActionView(BaseModel):
    id: str
    action_type: str
    display_summary: str
    expires_at: datetime
    status: str
    result: dict[str, Any] = Field(default_factory=dict)
