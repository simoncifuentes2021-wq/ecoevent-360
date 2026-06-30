"""default logistics reservation status

Revision ID: 20260628_0019
Revises: 20260624_0018
Create Date: 2026-06-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260628_0019"
down_revision: str | None = "20260624_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("update logistics_order_items set reservation_status = 'PENDING' where reservation_status is null")
    op.alter_column(
        "logistics_order_items",
        "reservation_status",
        existing_type=sa.String(length=40),
        nullable=False,
        server_default="PENDING",
    )


def downgrade() -> None:
    op.alter_column(
        "logistics_order_items",
        "reservation_status",
        existing_type=sa.String(length=40),
        nullable=True,
        server_default=None,
    )
