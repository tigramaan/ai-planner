"""set Europe/Moscow as the default user timezone

Revision ID: c4e72ab91f20
Revises: b7d4f9a2c801
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c4e72ab91f20"
down_revision: str | None = "b7d4f9a2c801"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.alter_column("timezone", server_default="Europe/Moscow")
    op.execute(sa.text("UPDATE users SET timezone = 'Europe/Moscow' WHERE timezone = 'UTC'"))


def downgrade() -> None:
    op.execute(sa.text("UPDATE users SET timezone = 'UTC' WHERE timezone = 'Europe/Moscow'"))
    with op.batch_alter_table("users") as batch:
        batch.alter_column("timezone", server_default="UTC")
