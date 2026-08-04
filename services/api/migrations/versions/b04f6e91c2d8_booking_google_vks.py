"""booking Google calendar and conference default

Revision ID: b04f6e91c2d8
Revises: a92d0c5e7b31
"""

import sqlalchemy as sa
from alembic import op

revision = "b04f6e91c2d8"
down_revision = "a92d0c5e7b31"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "booking_policies",
        sa.Column(
            "conference_provider",
            sa.String(32),
            nullable=False,
            server_default="google",
        ),
    )


def downgrade():
    op.drop_column("booking_policies", "conference_provider")
