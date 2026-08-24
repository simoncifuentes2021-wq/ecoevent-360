"""Add non-scaling box dimensions for editable report text.

Revision ID: 20260824_0057
Revises: 20260824_0056
"""

from alembic import op
import sqlalchemy as sa

revision = "20260824_0057"
down_revision = "20260824_0056"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("report_layout_overrides", sa.Column("box_width", sa.Float(), nullable=True))
    op.add_column("report_layout_overrides", sa.Column("box_height", sa.Float(), nullable=True))
    op.create_check_constraint(
        "ck_report_layout_overrides_box_width",
        "report_layout_overrides",
        "box_width is null or (box_width >= 24 and box_width <= 2000)",
    )
    op.create_check_constraint(
        "ck_report_layout_overrides_box_height",
        "report_layout_overrides",
        "box_height is null or (box_height >= 16 and box_height <= 3000)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_report_layout_overrides_box_height", "report_layout_overrides")
    op.drop_constraint("ck_report_layout_overrides_box_width", "report_layout_overrides")
    op.drop_column("report_layout_overrides", "box_height")
    op.drop_column("report_layout_overrides", "box_width")
