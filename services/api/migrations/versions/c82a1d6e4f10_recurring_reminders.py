"""recurring reminder series

Revision ID: c82a1d6e4f10
Revises: b04f6e91c2d8
"""

import sqlalchemy as sa
from alembic import op

revision = "c82a1d6e4f10"
down_revision = "b04f6e91c2d8"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("reminders", sa.Column("series_id", sa.String(36), nullable=True))
    op.add_column("reminders", sa.Column("recurrence_json", sa.JSON(), nullable=True))
    op.add_column(
        "reminders", sa.Column("paused", sa.Boolean(), nullable=False, server_default=sa.false())
    )
    op.create_index("ix_reminders_series_id", "reminders", ["series_id"])
    op.create_index("ix_reminders_paused", "reminders", ["paused"])


def downgrade():
    op.drop_index("ix_reminders_paused", table_name="reminders")
    op.drop_index("ix_reminders_series_id", table_name="reminders")
    op.drop_column("reminders", "paused")
    op.drop_column("reminders", "recurrence_json")
    op.drop_column("reminders", "series_id")
