from sqlalchemy import select

from app.config import get_settings
from app.database import SessionLocal
from app.models import AgentMessage, RecipientAlias, User
from app.recipient_aliases import (
    find_recipient_alias,
    remembered_recipient_request,
    save_recipient_alias,
)


def test_explicit_follow_up_saves_encrypted_recipient_alias(logged_in):
    with SessionLocal() as db:
        user = db.scalar(select(User))
        history = [
            AgentMessage(
                user_id=user.id,
                role="assistant",
                text=(
                    "Не нашёл адрес для: Анастасия Сорокина. "
                    "Укажите email или добавьте контакт."
                ),
            )
        ]
        requested = remembered_recipient_request(
            "sorokinanai@gmail.com и сохрани на будущее", history
        )
        assert requested == ("Анастасия Сорокина", "sorokinanai@gmail.com")
        row = save_recipient_alias(db, get_settings(), user, *requested)
        db.commit()
        assert "sorokinanai@gmail.com" not in row.encrypted_email
        assert find_recipient_alias(
            db, get_settings(), user, "анастасия   сорокина"
        ) == "sorokinanai@gmail.com"
        assert db.scalar(select(RecipientAlias)).user_id == user.id


def test_recipient_is_not_saved_without_explicit_request(logged_in):
    with SessionLocal() as db:
        user = db.scalar(select(User))
        history = [
            AgentMessage(
                user_id=user.id,
                role="assistant",
                text="No address found for: Anastasia Sorokina. Provide an email or add the contact.",
            )
        ]
        assert remembered_recipient_request("anastasia@example.com", history) is None
