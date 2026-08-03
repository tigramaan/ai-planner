"""Link due tasks to their push reminders.

Revision ID: d42b13c8e6a1
Revises: c31a6fb074d2
"""

from datetime import UTC, datetime
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision = "d42b13c8e6a1"
down_revision = "c31a6fb074d2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("reminders", sa.Column("task_id", sa.String(length=36), nullable=True))
    op.create_foreign_key(
        "fk_reminders_task_id_local_tasks",
        "reminders",
        "local_tasks",
        ["task_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_reminders_task_id", "reminders", ["task_id"], unique=True)

    connection = op.get_bind()
    tasks = sa.table(
        "local_tasks",
        sa.column("id", sa.String),
        sa.column("user_id", sa.String),
        sa.column("title", sa.String),
        sa.column("due_at", sa.DateTime(timezone=True)),
        sa.column("timezone", sa.String),
        sa.column("status", sa.String),
    )
    users = sa.table(
        "users",
        sa.column("id", sa.String),
        sa.column("locale", sa.String),
    )
    reminders = sa.table(
        "reminders",
        sa.column("id", sa.String),
        sa.column("user_id", sa.String),
        sa.column("task_id", sa.String),
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
            tasks.c.id,
            tasks.c.user_id,
            tasks.c.title,
            tasks.c.due_at,
            tasks.c.timezone,
            users.c.locale,
        )
        .join(users, users.c.id == tasks.c.user_id)
        .where(tasks.c.status == "open", tasks.c.due_at > now)
    ).all()
    if rows:
        op.bulk_insert(
            reminders,
            [
                {
                    "id": str(uuid4()),
                    "user_id": row.user_id,
                    "task_id": row.id,
                    "title": (
                        f"Срок задачи «{row.title}»"
                        if row.locale.startswith("ru")
                        else f'Task "{row.title}" is due'
                    ),
                    "due_at": row.due_at,
                    "timezone": row.timezone,
                    "channel": "push",
                    "status": "scheduled",
                    "attempts": 0,
                    "next_attempt_at": row.due_at,
                    "created_at": now,
                }
                for row in rows
            ],
        )


def downgrade() -> None:
    op.drop_index("ix_reminders_task_id", table_name="reminders")
    op.drop_constraint(
        "fk_reminders_task_id_local_tasks", "reminders", type_="foreignkey"
    )
    op.drop_column("reminders", "task_id")
