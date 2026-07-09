"""add form qr codes

Revision ID: 20260709_0029
Revises: 20260708_0028
Create Date: 2026-07-09 10:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260709_0029"
down_revision = "20260708_0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "form_qr_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("form_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("event_forms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("event_sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("label", sa.String(180), nullable=False),
        sa.Column("target_url", sa.Text(), nullable=False),
        sa.Column("qr_type", sa.String(50), server_default=sa.text("'FORM'"), nullable=False),
        sa.Column("language", sa.String(10), nullable=True),
        sa.Column("file_url", sa.Text(), nullable=True),
        sa.Column("file_path", sa.Text(), nullable=True),
        sa.Column("format", sa.String(20), server_default=sa.text("'PNG'"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("form_id", "qr_type", "language", name="uq_form_qr_codes_form_type_language"),
    )
    op.create_index("idx_form_qr_codes_form_id", "form_qr_codes", ["form_id"])
    op.create_index("idx_form_qr_codes_event_id", "form_qr_codes", ["event_id"])
    op.create_index("idx_form_qr_codes_session_id", "form_qr_codes", ["session_id"])
    op.create_index("idx_form_qr_codes_qr_type", "form_qr_codes", ["qr_type"])
    op.execute("alter table form_qr_codes enable row level security")
    op.execute(
        "create policy form_qr_codes_rls on form_qr_codes for all "
        "using (app_can_view_event(event_id)) with check (app_can_view_event(event_id))"
    )


def downgrade() -> None:
    op.execute("drop policy if exists form_qr_codes_rls on form_qr_codes")
    op.drop_table("form_qr_codes")
