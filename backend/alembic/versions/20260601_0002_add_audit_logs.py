"""add audit logs

Revision ID: 20260601_0002
Revises: 20260528_0001
Create Date: 2026-06-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260601_0002"
down_revision: str | None = "20260528_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("events.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clients.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("module", sa.String(length=120), nullable=False),
        sa.Column("entity_type", sa.String(length=120), nullable=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="SUCCESS"),
        sa.Column("old_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("new_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ip_address", sa.String(length=80), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("request_method", sa.String(length=20), nullable=True),
        sa.Column("request_path", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("idx_audit_logs_event_id", "audit_logs", ["event_id"])
    op.create_index("idx_audit_logs_client_id", "audit_logs", ["client_id"])
    op.create_index("idx_audit_logs_module", "audit_logs", ["module"])
    op.create_index("idx_audit_logs_action", "audit_logs", ["action"])
    op.create_index("idx_audit_logs_entity", "audit_logs", ["entity_type", "entity_id"])
    op.create_index("idx_audit_logs_created_at", "audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("idx_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("idx_audit_logs_entity", table_name="audit_logs")
    op.drop_index("idx_audit_logs_action", table_name="audit_logs")
    op.drop_index("idx_audit_logs_module", table_name="audit_logs")
    op.drop_index("idx_audit_logs_client_id", table_name="audit_logs")
    op.drop_index("idx_audit_logs_event_id", table_name="audit_logs")
    op.drop_index("idx_audit_logs_user_id", table_name="audit_logs")
    op.drop_table("audit_logs")
