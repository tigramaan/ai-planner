"""add encrypted per-user recipient aliases

Revision ID: d91e58c3a720
Revises: c4e72ab91f20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d91e58c3a720"
down_revision: str | None = "c4e72ab91f20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "recipient_aliases",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("normalized_name", sa.String(300), nullable=False),
        sa.Column("display_name", sa.String(300), nullable=False),
        sa.Column("encrypted_email", sa.Text(), nullable=False),
        sa.Column("email_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "normalized_name"),
    )
    op.create_index("ix_recipient_aliases_user_id", "recipient_aliases", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_recipient_aliases_user_id", table_name="recipient_aliases")
    op.drop_table("recipient_aliases")
