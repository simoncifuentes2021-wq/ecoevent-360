"""Add validated report editorial configuration.

Revision ID: 20260807_0044
Revises: 20260807_0043
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260807_0044"
down_revision = "20260807_0043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "reports",
        sa.Column("editorial_config", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )


def downgrade() -> None:
    op.drop_column("reports", "editorial_config")
