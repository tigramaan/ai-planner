"""single-use family invitation links

Revision ID: aa27c941e530
Revises: a4c8e71d9205
"""

import sqlalchemy as sa
from alembic import op

revision = "aa27c941e530"
down_revision = "a4c8e71d9205"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "family_invites",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        op.f("ix_family_invites_created_by_user_id"),
        "family_invites",
        ["created_by_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_family_invites_created_by_user_id"), table_name="family_invites")
    op.drop_table("family_invites")
