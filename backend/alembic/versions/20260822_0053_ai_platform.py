"""Add central AI generation audit and cache.

Revision ID: 20260822_0053
Revises: 20260821_0052
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260822_0053"
down_revision = "20260821_0052"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "ai_generations",
        sa.Column("id", UUID, server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("capability", sa.String(80), nullable=False),
        sa.Column("subject_type", sa.String(80), nullable=False),
        sa.Column("subject_id", UUID, nullable=False),
        sa.Column("event_id", UUID, sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("requested_by", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("model", sa.String(180), nullable=False),
        sa.Column("effective_model", sa.String(180)),
        sa.Column("prompt_version", sa.String(100), nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("input_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("output", postgresql.JSONB()),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("latency_ms", sa.Integer()),
        sa.Column("error_code", sa.String(80)),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("completed_at", sa.DateTime()),
        sa.CheckConstraint("status in ('PENDING','SUCCEEDED','FAILED')", name="ck_ai_generations_status"),
    )
    op.create_index(
        "idx_ai_generations_cache",
        "ai_generations",
        ["capability", "subject_id", "input_hash", "prompt_version", "provider", "model", "status"],
    )
    op.create_index("idx_ai_generations_event", "ai_generations", ["event_id", "created_at"])
    op.execute("alter table ai_generations enable row level security")
    op.execute("alter table ai_generations force row level security")
    op.execute(
        "create policy ai_generations_event_access on ai_generations for all "
        "using (app_can_view_event(event_id)) with check (app_can_view_event(event_id))"
    )


def downgrade() -> None:
    op.drop_table("ai_generations")
