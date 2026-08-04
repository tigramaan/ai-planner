from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class BookingPolicyWrite(BaseModel):
    enabled: bool = False
    duration_minutes: int = Field(default=30, ge=15, le=240, multiple_of=5)
    workdays: list[int] = Field(default=[0, 1, 2, 3, 4], min_length=1, max_length=7)
    work_start: str = Field(default="09:00", pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    work_end: str = Field(default="18:00", pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    minimum_notice_minutes: int = Field(default=120, ge=0, le=43200)
    horizon_days: int = Field(default=30, ge=1, le=90)
    buffer_before_minutes: int = Field(default=0, ge=0, le=240)
    buffer_after_minutes: int = Field(default=15, ge=0, le=240)
    max_per_day: int = Field(default=5, ge=1, le=50)
    title_template: str = Field(default="Звонок: {name}", min_length=1, max_length=200)

    @field_validator("workdays")
    @classmethod
    def valid_workdays(cls, value: list[int]) -> list[int]:
        if any(day < 0 or day > 6 for day in value) or len(set(value)) != len(value):
            raise ValueError("workdays must contain unique values from 0 to 6")
        return sorted(value)

    @field_validator("title_template")
    @classmethod
    def safe_template(cls, value: str) -> str:
        if "{name}" not in value:
            raise ValueError("title_template must contain {name}")
        return value.strip()


class BookingKeyCreate(BaseModel):
    name: str = Field(default="Website", min_length=1, max_length=100)


class BookingCreate(BaseModel):
    lead_id: str = Field(min_length=1, max_length=200)
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    start: datetime
    timezone: str = Field(min_length=1, max_length=64)
    company: str = Field(default="", max_length=200)
    note: str = Field(default="", max_length=1000)
