"""add event operational visibility flag

Revision ID: 20260604_0004
Revises: 20260601_0003
Create Date: 2026-06-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260604_0004"
down_revision: str | None = "20260601_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "events",
        sa.Column(
            "hidden_from_operations",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
    )


def downgrade() -> None:
    op.drop_column("events", "hidden_from_operations")
