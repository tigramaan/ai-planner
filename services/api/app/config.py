from functools import lru_cache

from pydantic import EmailStr, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    owner_email: EmailStr = "tigramaan@gmail.com"
    owner_initial_password: str = ""
    initial_setup_token: str = ""
    family_registration_code: str = ""
    secret_master_key: str = ""
    jwt_secret: str = ""
    database_url: str = "sqlite:///./planner.db"
    redis_url: str = "redis://localhost:6379/0"
    public_base_url: str = "http://localhost:3000"
    cookie_secure: bool = False
    cors_origins: str = "http://localhost:3000"
    allowed_hosts: str = "planner.umec.space,localhost,127.0.0.1,testserver,api"
    access_token_minutes: int = Field(1440, ge=5, le=10080)
    refresh_token_days: int = Field(30, ge=1, le=90)
    openai_api_key: str = ""
    openai_planner_model: str = "gpt-5.6-luna"
    openai_reasoning_effort: str = "low"
    openai_transcription_model: str = "whisper-1"
    google_client_id: str = ""
    google_client_secret: str = ""
    microsoft_client_id: str = ""
    microsoft_client_secret: str = ""
    microsoft_tenant: str = "common"
    zoom_client_id: str = ""
    zoom_client_secret: str = ""
    worker_service_token: str = ""
    vapid_public_key: str = ""

    @field_validator("owner_initial_password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        if value and len(value) < 12:
            raise ValueError("OWNER_INITIAL_PASSWORD must contain at least 12 characters")
        return value

    @field_validator("family_registration_code")
    @classmethod
    def registration_code_strength(cls, value: str) -> str:
        if value and len(value) < 16:
            raise ValueError("FAMILY_REGISTRATION_CODE must contain at least 16 characters")
        return value

    @field_validator("initial_setup_token")
    @classmethod
    def setup_token_strength(cls, value: str) -> str:
        if value and len(value) < 32:
            raise ValueError("INITIAL_SETUP_TOKEN must contain at least 32 characters")
        return value

    @field_validator("worker_service_token")
    @classmethod
    def worker_token_strength(cls, value: str) -> str:
        if value and len(value) < 32:
            raise ValueError("WORKER_SERVICE_TOKEN must contain at least 32 characters")
        return value

    @property
    def allowed_origins(self) -> list[str]:
        return [value.strip() for value in self.cors_origins.split(",") if value.strip()]

    @property
    def trusted_hosts(self) -> list[str]:
        return [value.strip() for value in self.allowed_hosts.split(",") if value.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
