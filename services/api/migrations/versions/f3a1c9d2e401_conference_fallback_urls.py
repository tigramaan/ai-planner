"""encrypted permanent conference fallback URLs

Revision ID: f3a1c9d2e401
Revises: e28a702f84b1
"""

import sqlalchemy as sa
from alembic import op

revision = "f3a1c9d2e401"
down_revision = "e28a702f84b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("fallback_teams_url_encrypted", sa.Text(), nullable=True))
        batch.add_column(sa.Column("fallback_telemost_url_encrypted", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_column("fallback_telemost_url_encrypted")
        batch.drop_column("fallback_teams_url_encrypted")
