"""add alerts and alert_audit tables

Revision ID: a2f7c8e3b401
Revises: 49645f988318
Create Date: 2026-02-27 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "a2f7c8e3b401"
down_revision = "49645f988318"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("alert_id", sa.String(64), unique=True, nullable=False, index=True),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("type", sa.String(50), nullable=False, index=True),
        sa.Column("severity", sa.String(20), nullable=False, index=True),
        sa.Column("affected_assets", postgresql.ARRAY(sa.String), server_default="{}"),
        sa.Column("summary", sa.Text, server_default=""),
        sa.Column("confidence_score", sa.Float, server_default="0"),
        sa.Column("event_score", sa.Float, server_default="0"),
        sa.Column("raw_payload", postgresql.JSONB, server_default="{}"),
    )

    op.create_table(
        "alert_audit",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("alert_id", sa.String(64), nullable=False, index=True),
        sa.Column("trace_id", sa.String(128), nullable=False),
        sa.Column("source_event_id", sa.String(128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("alert_audit")
    op.drop_table("alerts")
