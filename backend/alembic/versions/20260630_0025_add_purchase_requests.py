"""add purchase requests

Revision ID: 20260630_0025
Revises: 20260630_0024
Create Date: 2026-06-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260630_0025"
down_revision: str | None = "20260630_0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        do $$
        begin
            if not exists (select 1 from pg_type where typname = 'purchase_request_status') then
                create type purchase_request_status as enum (
                    'REQUESTED',
                    'APPROVED',
                    'REJECTED',
                    'PURCHASED',
                    'PARTIALLY_RECEIVED',
                    'RECEIVED',
                    'DELIVERED_DIRECT_TO_EVENT',
                    'CANCELLED'
                );
            end if;
            if not exists (select 1 from pg_type where typname = 'purchase_delivery_mode') then
                create type purchase_delivery_mode as enum (
                    'TO_WAREHOUSE',
                    'DIRECT_TO_EVENT'
                );
            end if;
        end $$;
        """
    )
    purchase_request_status = postgresql.ENUM(name="purchase_request_status", create_type=False)
    purchase_delivery_mode = postgresql.ENUM(name="purchase_delivery_mode", create_type=False)

    op.create_table(
        "purchase_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("events.id", ondelete="SET NULL"), nullable=True),
        sa.Column("logistics_order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("logistics_orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("purchased_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("received_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", purchase_request_status, server_default=sa.text("'REQUESTED'"), nullable=False),
        sa.Column("delivery_mode", purchase_delivery_mode, server_default=sa.text("'TO_WAREHOUSE'"), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("requested_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("rejected_at", sa.DateTime(), nullable=True),
        sa.Column("purchased_at", sa.DateTime(), nullable=True),
        sa.Column("received_at", sa.DateTime(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
        sa.Column("total_estimated_amount", sa.Numeric(12, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("total_purchased_amount", sa.Numeric(12, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.CheckConstraint("total_estimated_amount >= 0", name="ck_purchase_requests_total_estimated_non_negative"),
        sa.CheckConstraint("total_purchased_amount >= 0", name="ck_purchase_requests_total_purchased_non_negative"),
    )
    op.create_index("idx_purchase_requests_event_id", "purchase_requests", ["event_id"])
    op.create_index("idx_purchase_requests_logistics_order_id", "purchase_requests", ["logistics_order_id"])
    op.create_index("idx_purchase_requests_warehouse_id", "purchase_requests", ["warehouse_id"])
    op.create_index("idx_purchase_requests_status", "purchase_requests", ["status"])
    op.create_index("idx_purchase_requests_delivery_mode", "purchase_requests", ["delivery_mode"])

    op.create_table(
        "purchase_request_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("purchase_request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("purchase_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("logistics_order_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("logistics_order_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("inventory_items.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("item_name_snapshot", sa.String(length=180), nullable=False),
        sa.Column("unit_snapshot", sa.String(length=50), nullable=True),
        sa.Column("quantity_requested", sa.Numeric(12, 2), nullable=False),
        sa.Column("quantity_purchased", sa.Numeric(12, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("quantity_received", sa.Numeric(12, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("unit_price_estimated", sa.Numeric(12, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("unit_price_purchased", sa.Numeric(12, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("total_estimated", sa.Numeric(12, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("total_purchased", sa.Numeric(12, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.CheckConstraint("quantity_requested > 0", name="ck_purchase_request_items_requested_positive"),
        sa.CheckConstraint("quantity_purchased >= 0", name="ck_purchase_request_items_purchased_non_negative"),
        sa.CheckConstraint("quantity_received >= 0", name="ck_purchase_request_items_received_non_negative"),
        sa.CheckConstraint("unit_price_estimated >= 0", name="ck_purchase_request_items_estimated_price_non_negative"),
        sa.CheckConstraint("unit_price_purchased >= 0", name="ck_purchase_request_items_purchased_price_non_negative"),
        sa.CheckConstraint("total_estimated >= 0", name="ck_purchase_request_items_estimated_total_non_negative"),
        sa.CheckConstraint("total_purchased >= 0", name="ck_purchase_request_items_purchased_total_non_negative"),
    )
    op.create_index("idx_purchase_request_items_purchase_request_id", "purchase_request_items", ["purchase_request_id"])
    op.create_index("idx_purchase_request_items_logistics_order_item_id", "purchase_request_items", ["logistics_order_item_id"])
    op.create_index("idx_purchase_request_items_item_id", "purchase_request_items", ["item_id"])

    op.execute(
        """
        alter table purchase_requests enable row level security;
        alter table purchase_request_items enable row level security;

        create policy purchase_requests_rls on purchase_requests
            for all
            using (
                app_is_admin()
                or (
                    app_current_role() = 'SUPERVISOR'
                    and event_id is not null
                    and app_can_view_event(event_id)
                )
                or (
                    app_current_role() = 'LOGISTICS_OPERATOR'
                    and (
                        exists (
                            select 1
                            from logistics_orders lo
                            where lo.id = purchase_requests.logistics_order_id
                              and lo.assigned_operator_id = app_current_user_id()
                        )
                        or exists (
                            select 1
                            from warehouse_users wu
                            where wu.warehouse_id = purchase_requests.warehouse_id
                              and wu.user_id = app_current_user_id()
                              and wu.can_view_stock = true
                        )
                    )
                )
            )
            with check (
                app_is_admin()
                or (
                    app_current_role() = 'SUPERVISOR'
                    and event_id is not null
                    and app_can_view_event(event_id)
                )
                or (
                    app_current_role() = 'LOGISTICS_OPERATOR'
                    and exists (
                        select 1
                        from logistics_orders lo
                        where lo.id = purchase_requests.logistics_order_id
                          and lo.assigned_operator_id = app_current_user_id()
                    )
                )
            );

        create policy purchase_request_items_rls on purchase_request_items
            for all
            using (
                exists (
                    select 1
                    from purchase_requests pr
                    where pr.id = purchase_request_items.purchase_request_id
                )
            )
            with check (
                exists (
                    select 1
                    from purchase_requests pr
                    where pr.id = purchase_request_items.purchase_request_id
                )
            );
        """
    )


def downgrade() -> None:
    op.execute("drop policy if exists purchase_request_items_rls on purchase_request_items")
    op.execute("drop policy if exists purchase_requests_rls on purchase_requests")
    op.drop_index("idx_purchase_request_items_item_id", table_name="purchase_request_items")
    op.drop_index("idx_purchase_request_items_logistics_order_item_id", table_name="purchase_request_items")
    op.drop_index("idx_purchase_request_items_purchase_request_id", table_name="purchase_request_items")
    op.drop_table("purchase_request_items")
    op.drop_index("idx_purchase_requests_delivery_mode", table_name="purchase_requests")
    op.drop_index("idx_purchase_requests_status", table_name="purchase_requests")
    op.drop_index("idx_purchase_requests_warehouse_id", table_name="purchase_requests")
    op.drop_index("idx_purchase_requests_logistics_order_id", table_name="purchase_requests")
    op.drop_index("idx_purchase_requests_event_id", table_name="purchase_requests")
    op.drop_table("purchase_requests")
    op.execute("drop type if exists purchase_delivery_mode")
    op.execute("drop type if exists purchase_request_status")
