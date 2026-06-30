"""add stock movements

Revision ID: 20260624_0016
Revises: 20260624_0015
Create Date: 2026-06-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260624_0016"
down_revision: str | None = "20260624_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        do $$
        begin
            if not exists (select 1 from pg_type where typname = 'stock_movement_type') then
                create type stock_movement_type as enum (
                    'INITIAL_STOCK',
                    'ADJUSTMENT_IN',
                    'ADJUSTMENT_OUT',
                    'DAMAGE',
                    'LOSS',
                    'RECOVER_DAMAGED',
                    'CORRECTION',
                    'PURCHASE_IN',
                    'RESERVE',
                    'UNRESERVE',
                    'OUT_TO_EVENT',
                    'RETURN_FROM_EVENT'
                );
            end if;
        end $$;
        """
    )
    stock_movement_type = postgresql.ENUM(name="stock_movement_type", create_type=False)

    op.create_table(
        "stock_movements",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "warehouse_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("warehouses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("inventory_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "stock_balance_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("stock_balances.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("movement_type", stock_movement_type, nullable=False),
        sa.Column("quantity", sa.Numeric(12, 2), nullable=False),
        sa.Column("previous_quantity_on_hand", sa.Numeric(12, 2), nullable=True),
        sa.Column("new_quantity_on_hand", sa.Numeric(12, 2), nullable=True),
        sa.Column("previous_quantity_reserved", sa.Numeric(12, 2), nullable=True),
        sa.Column("new_quantity_reserved", sa.Numeric(12, 2), nullable=True),
        sa.Column("previous_quantity_damaged", sa.Numeric(12, 2), nullable=True),
        sa.Column("new_quantity_damaged", sa.Numeric(12, 2), nullable=True),
        sa.Column("reference_type", sa.String(length=80), nullable=True),
        sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_stock_movements_quantity_positive"),
    )
    op.create_index("idx_stock_movements_warehouse_id", "stock_movements", ["warehouse_id"])
    op.create_index("idx_stock_movements_item_id", "stock_movements", ["item_id"])
    op.create_index("idx_stock_movements_stock_balance_id", "stock_movements", ["stock_balance_id"])
    op.create_index("idx_stock_movements_movement_type", "stock_movements", ["movement_type"])
    op.create_index("idx_stock_movements_created_at", "stock_movements", ["created_at"])

    op.execute(
        """
        alter table stock_movements enable row level security;

        create policy stock_movements_rls on stock_movements
            for all
            using (
                app_is_admin()
                or app_current_role() = 'SUPERVISOR'
                or (
                    app_current_role() = 'LOGISTICS_OPERATOR'
                    and exists (
                        select 1
                        from warehouse_users wu
                        where wu.warehouse_id = stock_movements.warehouse_id
                          and wu.user_id = app_current_user_id()
                          and wu.can_view_stock = true
                    )
                )
            )
            with check (
                app_is_admin()
                or (
                    app_current_role() = 'LOGISTICS_OPERATOR'
                    and exists (
                        select 1
                        from warehouse_users wu
                        where wu.warehouse_id = stock_movements.warehouse_id
                          and wu.user_id = app_current_user_id()
                          and wu.can_manage_stock = true
                    )
                )
            );
        """
    )


def downgrade() -> None:
    op.execute("drop policy if exists stock_movements_rls on stock_movements")
    op.drop_index("idx_stock_movements_created_at", table_name="stock_movements")
    op.drop_index("idx_stock_movements_movement_type", table_name="stock_movements")
    op.drop_index("idx_stock_movements_stock_balance_id", table_name="stock_movements")
    op.drop_index("idx_stock_movements_item_id", table_name="stock_movements")
    op.drop_index("idx_stock_movements_warehouse_id", table_name="stock_movements")
    op.drop_table("stock_movements")
    op.execute("drop type if exists stock_movement_type")
