"""Add optimistic revision for logbook responsibility configuration.

Revision ID: 20260816_0048
Revises: 20260815_0047
"""
from alembic import op
import sqlalchemy as sa

revision = "20260816_0048"
down_revision = "20260815_0047"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "logbook_instances",
        sa.Column("configuration_revision", sa.Integer(), server_default="1", nullable=False),
    )
    op.create_check_constraint(
        "ck_logbook_instance_configuration_revision",
        "logbook_instances",
        "configuration_revision > 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_logbook_instance_configuration_revision",
        "logbook_instances",
        type_="check",
    )
    op.drop_column("logbook_instances", "configuration_revision")
