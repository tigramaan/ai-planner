from sqlalchemy import select

from app.database import SessionLocal
from app.models import Reminder, Timer
from app.routers import chat as chat_router
from app.schemas import Intent


def test_named_timer_start_reports_name_and_end_time(logged_in, monkeypatch):
    async def intent(*args, **kwargs):
        return Intent(intent="start_timer", title="Pasta", duration_minutes=1)

    monkeypatch.setattr(chat_router, "extract_intent", intent)

    response = logged_in.post("/api/v1/chat/messages", json={"text": "Start pasta timer"})

    assert response.status_code == 200
    assert 'Timer "Pasta" started for 1 minute, until ' in response.json()["message"]
    with SessionLocal() as db:
        timer = db.scalar(select(Timer).where(Timer.title == "Pasta"))
        assert timer is not None
        assert db.scalar(select(Reminder).where(Reminder.timer_id == timer.id)) is not None
