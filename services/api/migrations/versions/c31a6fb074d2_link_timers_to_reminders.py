"""Link timers to their push reminders.

Revision ID: c31a6fb074d2
Revises: b18f4c92d701
"""

from datetime import UTC, datetime
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision = "c31a6fb074d2"
down_revision = "b18f4c92d701"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("reminders", sa.Column("timer_id", sa.String(length=36), nullable=True))
    op.create_foreign_key(
        "fk_reminders_timer_id_timers",
        "reminders",
        "timers",
        ["timer_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_reminders_timer_id", "reminders", ["timer_id"], unique=True)

    connection = op.get_bind()
    timers = sa.table(
        "timers",
        sa.column("id", sa.String),
        sa.column("user_id", sa.String),
        sa.column("title", sa.String),
        sa.column("ends_at", sa.DateTime(timezone=True)),
        sa.column("status", sa.String),
    )
    users = sa.table(
        "users",
        sa.column("id", sa.String),
        sa.column("timezone", sa.String),
        sa.column("locale", sa.String),
    )
    reminders = sa.table(
        "reminders",
        sa.column("id", sa.String),
        sa.column("user_id", sa.String),
        sa.column("timer_id", sa.String),
        sa.column("title", sa.String),
        sa.column("due_at", sa.DateTime(timezone=True)),
        sa.column("timezone", sa.String),
        sa.column("channel", sa.String),
        sa.column("status", sa.String),
        sa.column("attempts", sa.Integer),
        sa.column("next_attempt_at", sa.DateTime(timezone=True)),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    now = datetime.now(UTC)
    rows = connection.execute(
        sa.select(
            timers.c.id,
            timers.c.user_id,
            timers.c.title,
            timers.c.ends_at,
            users.c.timezone,
            users.c.locale,
        )
        .join(users, users.c.id == timers.c.user_id)
        .where(timers.c.status == "active", timers.c.ends_at > now)
    ).all()
    if rows:
        op.bulk_insert(
            reminders,
            [
                {
                    "id": str(uuid4()),
                    "user_id": row.user_id,
                    "timer_id": row.id,
                    "title": (
                        f"Таймер «{row.title}» завершён"
                        if row.locale.startswith("ru")
                        else f'Timer "{row.title}" finished'
                    ),
                    "due_at": row.ends_at,
                    "timezone": row.timezone,
                    "channel": "push",
                    "status": "scheduled",
                    "attempts": 0,
                    "next_attempt_at": row.ends_at,
                    "created_at": now,
                }
                for row in rows
            ],
        )


def downgrade() -> None:
    op.drop_index("ix_reminders_timer_id", table_name="reminders")
    op.drop_constraint("fk_reminders_timer_id_timers", "reminders", type_="foreignkey")
    op.drop_column("reminders", "timer_id")
