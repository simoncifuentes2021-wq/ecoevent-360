"""add logistics preparation and dispatch

Revision ID: 20260628_0020
Revises: 20260628_0019
Create Date: 2026-06-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260628_0020"
down_revision: str | None = "20260628_0019"
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
    for value in ("IN_PREPARATION", "LOADED", "OUT_OF_WAREHOUSE"):
        _add_enum_value("logistics_order_status", value)

    op.add_column("logistics_orders", sa.Column("prepared_at", sa.DateTime(), nullable=True))
    op.add_column(
        "logistics_orders",
        sa.Column(
            "prepared_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column("logistics_orders", sa.Column("dispatched_at", sa.DateTime(), nullable=True))
    op.add_column(
        "logistics_orders",
        sa.Column(
            "dispatched_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column("logistics_orders", sa.Column("dispatch_notes", sa.Text(), nullable=True))
    op.create_index("idx_logistics_orders_prepared_by", "logistics_orders", ["prepared_by"])
    op.create_index("idx_logistics_orders_dispatched_by", "logistics_orders", ["dispatched_by"])

    op.add_column(
        "logistics_order_items",
        sa.Column("quantity_loaded", sa.Numeric(12, 2), server_default=sa.text("0"), nullable=False),
    )
    op.add_column(
        "logistics_order_items",
        sa.Column("quantity_dispatched", sa.Numeric(12, 2), server_default=sa.text("0"), nullable=False),
    )
    op.add_column(
        "logistics_order_items",
        sa.Column("preparation_status", sa.String(length=40), server_default="PENDING", nullable=False),
    )
    op.create_check_constraint(
        "ck_logistics_order_items_quantity_loaded_non_negative",
        "logistics_order_items",
        "quantity_loaded >= 0",
    )
    op.create_check_constraint(
        "ck_logistics_order_items_quantity_dispatched_non_negative",
        "logistics_order_items",
        "quantity_dispatched >= 0",
    )
    op.create_check_constraint(
        "ck_logistics_order_items_loaded_lte_reserved",
        "logistics_order_items",
        "quantity_loaded <= quantity_reserved",
    )
    op.create_check_constraint(
        "ck_logistics_order_items_dispatched_lte_loaded",
        "logistics_order_items",
        "quantity_dispatched <= quantity_loaded",
    )


def downgrade() -> None:
    op.drop_constraint("ck_logistics_order_items_dispatched_lte_loaded", "logistics_order_items", type_="check")
    op.drop_constraint("ck_logistics_order_items_loaded_lte_reserved", "logistics_order_items", type_="check")
    op.drop_constraint("ck_logistics_order_items_quantity_dispatched_non_negative", "logistics_order_items", type_="check")
    op.drop_constraint("ck_logistics_order_items_quantity_loaded_non_negative", "logistics_order_items", type_="check")
    op.drop_column("logistics_order_items", "preparation_status")
    op.drop_column("logistics_order_items", "quantity_dispatched")
    op.drop_column("logistics_order_items", "quantity_loaded")
    op.drop_index("idx_logistics_orders_dispatched_by", table_name="logistics_orders")
    op.drop_index("idx_logistics_orders_prepared_by", table_name="logistics_orders")
    op.drop_column("logistics_orders", "dispatch_notes")
    op.drop_column("logistics_orders", "dispatched_by")
    op.drop_column("logistics_orders", "dispatched_at")
    op.drop_column("logistics_orders", "prepared_by")
    op.drop_column("logistics_orders", "prepared_at")
