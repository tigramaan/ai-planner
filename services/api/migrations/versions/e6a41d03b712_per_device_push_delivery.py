"""Track Web Push delivery per browser subscription.

Revision ID: e6a41d03b712
Revises: d42b13c8e6a1
"""

import sqlalchemy as sa
from alembic import op

revision = "e6a41d03b712"
down_revision = "d42b13c8e6a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("reminders", sa.Column("target_subscription_id", sa.String(36)))
    op.create_foreign_key(
        "fk_reminders_target_subscription_id_push_subscriptions",
        "reminders", "push_subscriptions", ["target_subscription_id"], ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_reminders_target_subscription_id", "reminders", ["target_subscription_id"]
    )
    op.create_table(
        "push_deliveries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("reminder_id", sa.String(36), nullable=False),
        sa.Column("subscription_id", sa.String(36)),
        sa.Column("endpoint_hash", sa.String(64), nullable=False),
        sa.Column("provider", sa.String(80), nullable=False, server_default="web-push"),
        sa.Column("user_agent", sa.String(300), nullable=False, server_default="unknown"),
        sa.Column("status", sa.String(16), nullable=False, server_default="scheduled"),
        sa.Column("status_code", sa.Integer()),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.String(300)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["reminder_id"], ["reminders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["subscription_id"], ["push_subscriptions.id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint("reminder_id", "endpoint_hash"),
    )
    op.create_index("ix_push_deliveries_reminder_id", "push_deliveries", ["reminder_id"])
    op.create_index(
        "ix_push_deliveries_subscription_id", "push_deliveries", ["subscription_id"]
    )
    op.create_index("ix_push_deliveries_status", "push_deliveries", ["status"])


def downgrade() -> None:
    op.drop_table("push_deliveries")
    op.drop_index("ix_reminders_target_subscription_id", table_name="reminders")
    op.drop_constraint(
        "fk_reminders_target_subscription_id_push_subscriptions",
        "reminders", type_="foreignkey",
    )
    op.drop_column("reminders", "target_subscription_id")
