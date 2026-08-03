from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)
    device_name: str = Field(default="browser", max_length=160)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=256)
    registration_code: str = Field(min_length=1, max_length=256)
    device_name: str = Field(default="browser", max_length=160)


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
    model: str = Field(default="gpt-5-mini", max_length=100)
    transcription_model: str = Field(default="whisper-1", max_length=100)


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(default="", max_length=5000)
    due_at: datetime | None = None
    timezone: str = Field(default="Europe/Moscow", max_length=64)
    priority: Literal["low", "normal", "high"] = "normal"


class TimerCreate(BaseModel):
    title: str = Field(default="Таймер", max_length=300)
    duration_seconds: int = Field(ge=1, le=86400)


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


class Intent(BaseModel):
    intent: Literal[
        "show_today",
        "create_task",
        "create_reminder",
        "start_timer",
        "create_meeting",
        "send_email",
        "search_email",
        "unknown",
    ]
    title: str | None = None
    start_iso: str | None = None
    timezone: str | None = None
    duration_minutes: int | None = Field(default=None, ge=1, le=1440)
    participants: list[str] = Field(default_factory=list, max_length=50)
    provider: Literal["google", "microsoft", "local"] | None = None
    body: str | None = None
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
