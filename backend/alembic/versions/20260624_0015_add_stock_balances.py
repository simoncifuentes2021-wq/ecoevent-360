"""add stock balances

Revision ID: 20260624_0015
Revises: 20260624_0014
Create Date: 2026-06-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260624_0015"
down_revision: str | None = "20260624_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "stock_balances",
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
        sa.Column("quantity_on_hand", sa.Numeric(12, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("quantity_reserved", sa.Numeric(12, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("quantity_damaged", sa.Numeric(12, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.UniqueConstraint("warehouse_id", "item_id", name="uq_stock_balances_warehouse_item"),
        sa.CheckConstraint("quantity_on_hand >= 0", name="ck_stock_balances_on_hand_non_negative"),
        sa.CheckConstraint("quantity_reserved >= 0", name="ck_stock_balances_reserved_non_negative"),
        sa.CheckConstraint("quantity_damaged >= 0", name="ck_stock_balances_damaged_non_negative"),
        sa.CheckConstraint(
            "quantity_reserved <= quantity_on_hand",
            name="ck_stock_balances_reserved_lte_on_hand",
        ),
        sa.CheckConstraint(
            "quantity_damaged <= quantity_on_hand",
            name="ck_stock_balances_damaged_lte_on_hand",
        ),
        sa.CheckConstraint(
            "(quantity_on_hand - quantity_reserved - quantity_damaged) >= 0",
            name="ck_stock_balances_available_non_negative",
        ),
    )
    op.create_index("idx_stock_balances_warehouse_id", "stock_balances", ["warehouse_id"])
    op.create_index("idx_stock_balances_item_id", "stock_balances", ["item_id"])

    op.execute(
        """
        alter table stock_balances enable row level security;

        create policy stock_balances_rls on stock_balances
            for all
            using (
                app_is_admin()
                or app_current_role() = 'SUPERVISOR'
                or (
                    app_current_role() = 'LOGISTICS_OPERATOR'
                    and exists (
                        select 1
                        from warehouse_users wu
                        where wu.warehouse_id = stock_balances.warehouse_id
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
                        where wu.warehouse_id = stock_balances.warehouse_id
                          and wu.user_id = app_current_user_id()
                          and wu.can_manage_stock = true
                    )
                )
            );
        """
    )


def downgrade() -> None:
    op.execute("drop policy if exists stock_balances_rls on stock_balances")
    op.drop_index("idx_stock_balances_item_id", table_name="stock_balances")
    op.drop_index("idx_stock_balances_warehouse_id", table_name="stock_balances")
    op.drop_table("stock_balances")
