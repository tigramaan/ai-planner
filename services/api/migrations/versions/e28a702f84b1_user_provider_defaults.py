"""add user provider defaults

Revision ID: e28a702f84b1
Revises: d91e58c3a720
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e28a702f84b1"
down_revision: str | None = "d91e58c3a720"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("default_calendar", sa.String(32), nullable=False, server_default="google"))
        batch.add_column(sa.Column("default_mail", sa.String(32), nullable=False, server_default="google"))
        batch.add_column(sa.Column("default_conference", sa.String(32), nullable=False, server_default="none"))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_column("default_conference")
        batch.drop_column("default_mail")
        batch.drop_column("default_calendar")
