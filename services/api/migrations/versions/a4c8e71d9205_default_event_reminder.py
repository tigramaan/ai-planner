"""default calendar event reminder

Revision ID: a4c8e71d9205
Revises: f3a1c9d2e401
"""

import sqlalchemy as sa
from alembic import op

revision = "a4c8e71d9205"
down_revision = "f3a1c9d2e401"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(
            sa.Column("default_reminder_minutes", sa.Integer(), nullable=False, server_default="5")
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_column("default_reminder_minutes")
