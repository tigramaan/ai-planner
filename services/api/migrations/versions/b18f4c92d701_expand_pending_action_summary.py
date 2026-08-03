"""Expand pending action summaries for complete email previews.

Revision ID: b18f4c92d701
Revises: aa27c941e530
"""

import sqlalchemy as sa
from alembic import op

revision = "b18f4c92d701"
down_revision = "aa27c941e530"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "pending_actions",
        "display_summary",
        existing_type=sa.String(length=500),
        type_=sa.Text(),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "pending_actions",
        "display_summary",
        existing_type=sa.Text(),
        type_=sa.String(length=500),
        existing_nullable=False,
    )
