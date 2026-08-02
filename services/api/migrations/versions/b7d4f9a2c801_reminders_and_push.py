"""reminders and encrypted push subscriptions

Revision ID: b7d4f9a2c801
Revises: 4e84b0035851
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b7d4f9a2c801"
down_revision: str | None = "4e84b0035851"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reminders",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("channel", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(length=300), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_reminders_user_id"), "reminders", ["user_id"])
    op.create_index(op.f("ix_reminders_due_at"), "reminders", ["due_at"])
    op.create_index(op.f("ix_reminders_status"), "reminders", ["status"])
    op.create_index(op.f("ix_reminders_next_attempt_at"), "reminders", ["next_attempt_at"])
    op.create_table(
        "push_subscriptions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("endpoint_hash", sa.String(length=64), nullable=False),
        sa.Column("encrypted_subscription", sa.Text(), nullable=False),
        sa.Column("user_agent", sa.String(length=300), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "endpoint_hash"),
    )
    op.create_index(op.f("ix_push_subscriptions_user_id"), "push_subscriptions", ["user_id"])
    op.create_index(
        op.f("ix_push_subscriptions_endpoint_hash"),
        "push_subscriptions",
        ["endpoint_hash"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_push_subscriptions_endpoint_hash"), table_name="push_subscriptions")
    op.drop_index(op.f("ix_push_subscriptions_user_id"), table_name="push_subscriptions")
    op.drop_table("push_subscriptions")
    op.drop_index(op.f("ix_reminders_next_attempt_at"), table_name="reminders")
    op.drop_index(op.f("ix_reminders_status"), table_name="reminders")
    op.drop_index(op.f("ix_reminders_due_at"), table_name="reminders")
    op.drop_index(op.f("ix_reminders_user_id"), table_name="reminders")
    op.drop_table("reminders")
