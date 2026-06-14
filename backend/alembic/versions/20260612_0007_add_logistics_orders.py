"""add logistics orders module

Revision ID: 20260612_0007
Revises: 20260610_0006
Create Date: 2026-06-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260612_0007"
down_revision: str | None = "20260610_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        do $$
        begin
            if not exists (select 1 from pg_type where typname = 'order_status') then
                create type order_status as enum (
                    'DRAFT', 'REQUESTED', 'APPROVED', 'PREPARING', 'LOADED',
                    'IN_TRANSIT', 'DELIVERED', 'RETURN_IN_PROGRESS',
                    'RETURNED', 'CLOSED', 'CANCELLED'
                );
            end if;
            if not exists (select 1 from pg_type where typname = 'order_item_stage_status') then
                create type order_item_stage_status as enum ('PENDING', 'COMPLETED', 'OBSERVED');
            end if;
            if not exists (select 1 from pg_type where typname = 'order_evidence_stage') then
                create type order_evidence_stage as enum ('LOAD', 'DELIVERY', 'RETURN');
            end if;
        end $$;
        """
    )

    order_status = postgresql.ENUM(name="order_status", create_type=False)
    order_item_stage_status = postgresql.ENUM(name="order_item_stage_status", create_type=False)
    order_evidence_stage = postgresql.ENUM(name="order_evidence_stage", create_type=False)

    op.create_table(
        "catalog_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("category", sa.String(length=120), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("unit", sa.String(length=50), nullable=True),
        sa.Column("default_unit_price", sa.Numeric(12, 2), server_default=sa.text("0"), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("TRUE"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("idx_catalog_items_category", "catalog_items", ["category"])
    op.create_index("idx_catalog_items_is_active", "catalog_items", ["is_active"])

    op.create_table(
        "event_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", order_status, server_default=sa.text("'DRAFT'"), nullable=False),
        sa.Column("requested_date", sa.DateTime(), nullable=True),
        sa.Column("required_date", sa.DateTime(), nullable=True),
        sa.Column("total_amount", sa.Numeric(12, 2), server_default=sa.text("0"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("idx_event_orders_event_id", "event_orders", ["event_id"])
    op.create_index("idx_event_orders_assigned_to", "event_orders", ["assigned_to"])
    op.create_index("idx_event_orders_status", "event_orders", ["status"])

    op.create_table(
        "event_order_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("event_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("catalog_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("catalog_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("zone_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("event_zones.id", ondelete="SET NULL"), nullable=True),
        sa.Column("item_name_snapshot", sa.String(length=180), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 2), nullable=False),
        sa.Column("unit", sa.String(length=50), nullable=True),
        sa.Column("unit_price", sa.Numeric(12, 2), server_default=sa.text("0"), nullable=True),
        sa.Column("total_price", sa.Numeric(12, 2), server_default=sa.text("0"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("load_status", order_item_stage_status, server_default=sa.text("'PENDING'"), nullable=False),
        sa.Column("delivery_status", order_item_stage_status, server_default=sa.text("'PENDING'"), nullable=False),
        sa.Column("return_status", order_item_stage_status, server_default=sa.text("'PENDING'"), nullable=False),
        sa.Column("loaded_at", sa.DateTime(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
        sa.Column("returned_at", sa.DateTime(), nullable=True),
        sa.Column("loaded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("delivered_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("returned_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("load_observation", sa.Text(), nullable=True),
        sa.Column("delivery_observation", sa.Text(), nullable=True),
        sa.Column("return_observation", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.CheckConstraint("quantity > 0"),
        sa.CheckConstraint("unit_price >= 0"),
    )
    op.create_index("idx_event_order_items_order_id", "event_order_items", ["order_id"])
    op.create_index("idx_event_order_items_catalog_item_id", "event_order_items", ["catalog_item_id"])
    op.create_index("idx_event_order_items_zone_id", "event_order_items", ["zone_id"])

    op.create_table(
        "order_evidences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("event_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("event_order_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("stage", order_evidence_stage, nullable=False),
        sa.Column("file_url", sa.Text(), nullable=False),
        sa.Column("file_type", sa.String(length=80), nullable=True),
        sa.Column("file_name", sa.String(length=255), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("visible_to_client", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("idx_order_evidences_event_id", "order_evidences", ["event_id"])
    op.create_index("idx_order_evidences_order_id", "order_evidences", ["order_id"])
    op.create_index("idx_order_evidences_order_item_id", "order_evidences", ["order_item_id"])
    op.create_index("idx_order_evidences_stage", "order_evidences", ["stage"])

    op.execute(
        """
        create or replace function app_can_view_order(order_uuid uuid)
        returns boolean
        language sql
        stable
        security definer
        set search_path = public
        as $$
            select exists (
                select 1
                from event_orders eo
                where eo.id = order_uuid
                  and (
                    app_can_view_event(eo.event_id)
                    or eo.assigned_to = app_current_user_id()
                  )
            )
        $$;

        alter table catalog_items enable row level security;
        alter table event_orders enable row level security;
        alter table event_order_items enable row level security;
        alter table order_evidences enable row level security;

        create policy catalog_items_rls on catalog_items
            for all
            using (app_current_role() in ('SUPER_ADMIN', 'ADMIN', 'SUPERVISOR', 'WORKER'))
            with check (app_is_admin());

        create policy event_orders_rls on event_orders
            for all
            using (app_can_view_order(id))
            with check (app_is_admin() or app_can_view_event(event_id));

        create policy event_order_items_rls on event_order_items
            for all
            using (app_can_view_order(order_id))
            with check (app_can_view_order(order_id));

        create policy order_evidences_rls on order_evidences
            for all
            using (
                app_can_view_order(order_id)
                and (
                    app_current_role() <> 'CLIENT'
                    or visible_to_client = true
                )
            )
            with check (
                app_current_role() in ('SUPER_ADMIN', 'ADMIN', 'SUPERVISOR', 'WORKER')
                and app_can_view_order(order_id)
            );
        """
    )


def downgrade() -> None:
    op.execute("drop policy if exists order_evidences_rls on order_evidences")
    op.execute("drop policy if exists event_order_items_rls on event_order_items")
    op.execute("drop policy if exists event_orders_rls on event_orders")
    op.execute("drop policy if exists catalog_items_rls on catalog_items")
    op.execute("drop function if exists app_can_view_order(uuid)")
    op.drop_table("order_evidences")
    op.drop_table("event_order_items")
    op.drop_table("event_orders")
    op.drop_table("catalog_items")
    op.execute("drop type if exists order_evidence_stage")
    op.execute("drop type if exists order_item_stage_status")
    op.execute("drop type if exists order_status")
