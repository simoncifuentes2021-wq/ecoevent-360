"""Add typed visual layout variants to report sections.

Revision ID: 20260806_0042
Revises: 20260806_0041
"""

from alembic import op
import sqlalchemy as sa


revision = "20260806_0042"
down_revision = "20260806_0041"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "report_sections",
        sa.Column(
            "layout_variant",
            sa.String(30),
            server_default="EDITORIAL",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("report_sections", "layout_variant")
