"""Add visual overrides for the original AUTO report renderer.

Revision ID: 20260824_0056
Revises: 20260824_0055
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260824_0056"
down_revision = "20260824_0055"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "report_layout_overrides",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("reports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("element_key", sa.String(220), nullable=False),
        sa.Column("page_key", sa.String(160)),
        sa.Column("x_offset", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("y_offset", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("width_scale", sa.Float(), nullable=False, server_default=sa.text("1")),
        sa.Column("height_scale", sa.Float(), nullable=False, server_default=sa.text("1")),
        sa.Column("rotation", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("z_index", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("locked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("visible", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("report_id", "element_key", name="uq_report_layout_overrides_report_key"),
        sa.CheckConstraint("width_scale >= 0.1 and width_scale <= 5", name="ck_report_layout_overrides_width_scale"),
        sa.CheckConstraint("height_scale >= 0.1 and height_scale <= 5", name="ck_report_layout_overrides_height_scale"),
        sa.CheckConstraint("rotation >= -360 and rotation <= 360", name="ck_report_layout_overrides_rotation"),
    )
    op.create_index("idx_report_layout_overrides_report", "report_layout_overrides", ["report_id"])
    op.execute("alter table report_layout_overrides enable row level security")
    op.execute("alter table report_layout_overrides force row level security")
    op.execute("create policy report_layout_overrides_admin on report_layout_overrides for all using (app_is_admin()) with check (app_is_admin())")


def downgrade() -> None:
    op.drop_table("report_layout_overrides")
