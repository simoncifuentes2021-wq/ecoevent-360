"""add context fields to audit logs

Revision ID: 20260601_0003
Revises: 20260601_0002
Create Date: 2026-06-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260601_0003"
down_revision: str | None = "20260601_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "audit_logs",
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "audit_logs",
        sa.Column(
            "incident_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("incidents.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "audit_logs",
        sa.Column(
            "zone_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("event_zones.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column("audit_logs", sa.Column("description", sa.Text(), nullable=True))
    op.create_index("idx_audit_logs_task_id", "audit_logs", ["task_id"])
    op.create_index("idx_audit_logs_incident_id", "audit_logs", ["incident_id"])
    op.create_index("idx_audit_logs_zone_id", "audit_logs", ["zone_id"])


def downgrade() -> None:
    op.drop_index("idx_audit_logs_zone_id", table_name="audit_logs")
    op.drop_index("idx_audit_logs_incident_id", table_name="audit_logs")
    op.drop_index("idx_audit_logs_task_id", table_name="audit_logs")
    op.drop_column("audit_logs", "description")
    op.drop_column("audit_logs", "zone_id")
    op.drop_column("audit_logs", "incident_id")
    op.drop_column("audit_logs", "task_id")

