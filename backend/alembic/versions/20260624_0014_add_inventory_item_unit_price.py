"""add unit price to inventory items

Revision ID: 20260624_0014
Revises: 20260624_0013
Create Date: 2026-06-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260624_0014"
down_revision: str | None = "20260624_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "inventory_items",
        sa.Column(
            "unit_price",
            sa.Numeric(12, 2),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_inventory_items_unit_price_non_negative",
        "inventory_items",
        "unit_price >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_inventory_items_unit_price_non_negative",
        "inventory_items",
        type_="check",
    )
    op.drop_column("inventory_items", "unit_price")
