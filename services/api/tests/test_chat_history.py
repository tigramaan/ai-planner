from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.database import SessionLocal
from app.models import AgentMessage, User


def test_chat_history_returns_latest_fifty_in_chronological_order(logged_in):
    start = datetime(2026, 8, 1, tzinfo=UTC)
    with SessionLocal() as db:
        user = db.scalar(select(User))
        db.add_all(
            AgentMessage(
                user_id=user.id,
                role="user" if index % 2 == 0 else "assistant",
                text=f"message-{index:02d}",
                created_at=start + timedelta(seconds=index),
            )
            for index in range(55)
        )
        db.commit()

    response = logged_in.get("/api/v1/chat/messages")

    assert response.status_code == 200
    assert len(response.json()) == 50
    assert [row["text"] for row in response.json()] == [
        f"message-{index:02d}" for index in range(5, 55)
    ]
