"""booking api

Revision ID: f8c1b0a41e20
Revises: e6a41d03b712
"""

import sqlalchemy as sa
from alembic import op

revision = "f8c1b0a41e20"
down_revision = "e6a41d03b712"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "booking_policies",
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("workdays", sa.JSON(), nullable=False),
        sa.Column("work_start", sa.String(5), nullable=False, server_default="09:00"),
        sa.Column("work_end", sa.String(5), nullable=False, server_default="18:00"),
        sa.Column("minimum_notice_minutes", sa.Integer(), nullable=False, server_default="120"),
        sa.Column("horizon_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("buffer_before_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("buffer_after_minutes", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("max_per_day", sa.Integer(), nullable=False, server_default="5"),
        sa.Column(
            "title_template", sa.String(200), nullable=False, server_default="Звонок: {name}"
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "booking_api_keys",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("key_prefix", sa.String(16), nullable=False),
        sa.Column("key_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_booking_api_keys_user_id", "booking_api_keys", ["user_id"])
    op.create_table(
        "bookings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "api_key_id",
            sa.String(36),
            sa.ForeignKey("booking_api_keys.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("lead_hash", sa.String(64), nullable=False),
        sa.Column("idempotency_key", sa.String(100), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("slot_lock", sa.String(100), unique=True),
        sa.Column("contact_encrypted", sa.Text(), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("provider_event_id", sa.String(300)),
        sa.Column("result_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("api_key_id", "idempotency_key"),
    )
    for name, columns in (
        ("ix_bookings_user_id", ["user_id"]),
        ("ix_bookings_api_key_id", ["api_key_id"]),
        ("ix_bookings_lead_hash", ["lead_hash"]),
        ("ix_bookings_start_at", ["start_at"]),
        ("ix_bookings_status", ["status"]),
    ):
        op.create_index(name, "bookings", columns)


def downgrade():
    op.drop_table("bookings")
    op.drop_table("booking_api_keys")
    op.drop_table("booking_policies")
