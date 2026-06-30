"""add logistics delivery

Revision ID: 20260629_0021
Revises: 20260628_0020
Create Date: 2026-06-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260629_0021"
down_revision: str | None = "20260628_0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _add_enum_value(enum_name: str, value: str) -> None:
    op.execute(
        f"""
        do $$
        begin
            if not exists (
                select 1
                from pg_enum e
                join pg_type t on t.oid = e.enumtypid
                where t.typname = '{enum_name}'
                  and e.enumlabel = '{value}'
            ) then
                alter type {enum_name} add value '{value}';
            end if;
        end $$;
        """
    )


def upgrade() -> None:
    for value in ("DELIVERED", "PARTIALLY_DELIVERED"):
        _add_enum_value("logistics_order_status", value)

    op.add_column("logistics_orders", sa.Column("delivered_at", sa.DateTime(), nullable=True))
    op.add_column(
        "logistics_orders",
        sa.Column(
            "delivered_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("idx_logistics_orders_delivered_by", "logistics_orders", ["delivered_by"])

    op.add_column(
        "logistics_order_items",
        sa.Column("quantity_delivered", sa.Numeric(12, 2), server_default=sa.text("0"), nullable=False),
    )
    op.add_column(
        "logistics_order_items",
        sa.Column("delivery_status", sa.String(length=40), server_default="PENDING", nullable=False),
    )
    op.create_check_constraint(
        "ck_logistics_order_items_quantity_delivered_non_negative",
        "logistics_order_items",
        "quantity_delivered >= 0",
    )
    op.create_check_constraint(
        "ck_logistics_order_items_delivered_lte_dispatched",
        "logistics_order_items",
        "quantity_delivered <= quantity_dispatched",
    )


def downgrade() -> None:
    op.drop_constraint("ck_logistics_order_items_delivered_lte_dispatched", "logistics_order_items", type_="check")
    op.drop_constraint("ck_logistics_order_items_quantity_delivered_non_negative", "logistics_order_items", type_="check")
    op.drop_column("logistics_order_items", "delivery_status")
    op.drop_column("logistics_order_items", "quantity_delivered")
    op.drop_index("idx_logistics_orders_delivered_by", table_name="logistics_orders")
    op.drop_column("logistics_orders", "delivered_by")
    op.drop_column("logistics_orders", "delivered_at")
