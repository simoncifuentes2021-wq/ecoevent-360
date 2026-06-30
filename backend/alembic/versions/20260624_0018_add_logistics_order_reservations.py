"""add logistics order reservations

Revision ID: 20260624_0018
Revises: 20260624_0017
Create Date: 2026-06-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260624_0018"
down_revision: str | None = "20260624_0017"
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
    for value in ("STOCK_REVIEW", "RESERVED", "INSUFFICIENT_STOCK"):
        _add_enum_value("logistics_order_status", value)

    op.add_column("logistics_orders", sa.Column("reserved_at", sa.DateTime(), nullable=True))
    op.add_column(
        "logistics_orders",
        sa.Column(
            "reserved_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("idx_logistics_orders_reserved_by", "logistics_orders", ["reserved_by"])

    op.add_column(
        "logistics_order_items",
        sa.Column("quantity_reserved", sa.Numeric(12, 2), server_default=sa.text("0"), nullable=False),
    )
    op.add_column(
        "logistics_order_items",
        sa.Column("quantity_missing", sa.Numeric(12, 2), server_default=sa.text("0"), nullable=False),
    )
    op.add_column(
        "logistics_order_items",
        sa.Column("reservation_status", sa.String(length=40), nullable=True),
    )
    op.create_check_constraint(
        "ck_logistics_order_items_quantity_reserved_non_negative",
        "logistics_order_items",
        "quantity_reserved >= 0",
    )
    op.create_check_constraint(
        "ck_logistics_order_items_quantity_missing_non_negative",
        "logistics_order_items",
        "quantity_missing >= 0",
    )
    op.create_check_constraint(
        "ck_logistics_order_items_reserved_lte_requested",
        "logistics_order_items",
        "quantity_reserved <= quantity_requested",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_logistics_order_items_reserved_lte_requested",
        "logistics_order_items",
        type_="check",
    )
    op.drop_constraint(
        "ck_logistics_order_items_quantity_missing_non_negative",
        "logistics_order_items",
        type_="check",
    )
    op.drop_constraint(
        "ck_logistics_order_items_quantity_reserved_non_negative",
        "logistics_order_items",
        type_="check",
    )
    op.drop_column("logistics_order_items", "reservation_status")
    op.drop_column("logistics_order_items", "quantity_missing")
    op.drop_column("logistics_order_items", "quantity_reserved")
    op.drop_index("idx_logistics_orders_reserved_by", table_name="logistics_orders")
    op.drop_column("logistics_orders", "reserved_by")
    op.drop_column("logistics_orders", "reserved_at")
