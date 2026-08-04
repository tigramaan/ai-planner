from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.database import SessionLocal
from app.models import AgentMessage


def test_chat_removes_messages_older_than_one_hundred_days(logged_in):
    with SessionLocal() as db:
        user_id = logged_in.get("/api/v1/me").json()["id"]
        old = AgentMessage(
            user_id=user_id,
            role="user",
            text="Старое сообщение",
            created_at=datetime.now(UTC) - timedelta(days=101),
        )
        recent = AgentMessage(user_id=user_id, role="assistant", text="Новое сообщение")
        db.add_all([old, recent])
        db.commit()
        old_id = old.id

    response = logged_in.get("/api/v1/chat/messages")
    assert response.status_code == 200
    assert "Старое сообщение" not in {row["text"] for row in response.json()}
    assert "Новое сообщение" in {row["text"] for row in response.json()}
    with SessionLocal() as db:
        assert db.scalar(select(AgentMessage).where(AgentMessage.id == old_id)) is None
