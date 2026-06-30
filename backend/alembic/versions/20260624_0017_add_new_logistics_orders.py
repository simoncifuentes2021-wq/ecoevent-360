"""add new logistics orders

Revision ID: 20260624_0017
Revises: 20260624_0016
Create Date: 2026-06-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260624_0017"
down_revision: str | None = "20260624_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        do $$
        begin
            if not exists (select 1 from pg_type where typname = 'logistics_order_status') then
                create type logistics_order_status as enum (
                    'REQUESTED',
                    'ASSIGNED',
                    'OBSERVED',
                    'CANCELLED'
                );
            end if;
        end $$;
        """
    )
    logistics_order_status = postgresql.ENUM(name="logistics_order_status", create_type=False)

    op.create_table(
        "logistics_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("assigned_operator_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", logistics_order_status, server_default=sa.text("'REQUESTED'"), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("delivery_zone", sa.String(length=180), nullable=True),
        sa.Column("delivery_notes", sa.Text(), nullable=True),
        sa.Column("total_estimated_amount", sa.Numeric(12, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("idx_logistics_orders_event_id", "logistics_orders", ["event_id"])
    op.create_index("idx_logistics_orders_warehouse_id", "logistics_orders", ["warehouse_id"])
    op.create_index("idx_logistics_orders_assigned_operator_id", "logistics_orders", ["assigned_operator_id"])
    op.create_index("idx_logistics_orders_status", "logistics_orders", ["status"])

    op.create_table(
        "logistics_order_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("logistics_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("inventory_items.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("item_name_snapshot", sa.String(length=180), nullable=False),
        sa.Column("item_type_snapshot", sa.String(length=60), nullable=False),
        sa.Column("unit_snapshot", sa.String(length=50), nullable=True),
        sa.Column("quantity_requested", sa.Numeric(12, 2), nullable=False),
        sa.Column("unit_price_snapshot", sa.Numeric(12, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("total_price", sa.Numeric(12, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.CheckConstraint("quantity_requested > 0", name="ck_logistics_order_items_quantity_positive"),
        sa.CheckConstraint("unit_price_snapshot >= 0", name="ck_logistics_order_items_unit_price_non_negative"),
        sa.CheckConstraint("total_price >= 0", name="ck_logistics_order_items_total_price_non_negative"),
    )
    op.create_index("idx_logistics_order_items_order_id", "logistics_order_items", ["order_id"])
    op.create_index("idx_logistics_order_items_item_id", "logistics_order_items", ["item_id"])

    op.execute(
        """
        alter table logistics_orders enable row level security;
        alter table logistics_order_items enable row level security;

        create policy logistics_orders_rls on logistics_orders
            for all
            using (
                app_is_admin()
                or (
                    app_current_role() = 'SUPERVISOR'
                    and app_can_view_event(event_id)
                )
                or (
                    app_current_role() = 'LOGISTICS_OPERATOR'
                    and assigned_operator_id = app_current_user_id()
                )
            )
            with check (
                app_is_admin()
                or (
                    app_current_role() = 'SUPERVISOR'
                    and app_can_view_event(event_id)
                )
            );

        create policy logistics_order_items_rls on logistics_order_items
            for all
            using (
                exists (
                    select 1
                    from logistics_orders lo
                    where lo.id = logistics_order_items.order_id
                )
            )
            with check (
                exists (
                    select 1
                    from logistics_orders lo
                    where lo.id = logistics_order_items.order_id
                )
            );
        """
    )


def downgrade() -> None:
    op.execute("drop policy if exists logistics_order_items_rls on logistics_order_items")
    op.execute("drop policy if exists logistics_orders_rls on logistics_orders")
    op.drop_index("idx_logistics_order_items_item_id", table_name="logistics_order_items")
    op.drop_index("idx_logistics_order_items_order_id", table_name="logistics_order_items")
    op.drop_table("logistics_order_items")
    op.drop_index("idx_logistics_orders_status", table_name="logistics_orders")
    op.drop_index("idx_logistics_orders_assigned_operator_id", table_name="logistics_orders")
    op.drop_index("idx_logistics_orders_warehouse_id", table_name="logistics_orders")
    op.drop_index("idx_logistics_orders_event_id", table_name="logistics_orders")
    op.drop_table("logistics_orders")
    op.execute("drop type if exists logistics_order_status")
