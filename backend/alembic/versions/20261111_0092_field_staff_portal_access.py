"""Allow administrators to revoke field staff portal access per event.

Revision ID: 20261111_0092
Revises: 20261110_0091
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261111_0092"
down_revision: str | None = "20261110_0091"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "events",
        sa.Column(
            "field_staff_portal_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("TRUE"),
        ),
    )


def downgrade() -> None:
    op.drop_column("events", "field_staff_portal_enabled")
