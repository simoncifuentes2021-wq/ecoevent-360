"""add logistics evidences

Revision ID: 20260703_0026
Revises: 20260630_0025
Create Date: 2026-07-03 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260703_0026"
down_revision = "20260630_0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        do $$
        begin
            if not exists (select 1 from pg_type where typname = 'logistics_evidence_stage') then
                create type logistics_evidence_stage as enum (
                    'LOGISTICS_PREPARATION',
                    'LOGISTICS_LOADING',
                    'LOGISTICS_DISPATCH',
                    'LOGISTICS_DELIVERY',
                    'LOGISTICS_OUTCOME',
                    'LOGISTICS_RETURN',
                    'LOGISTICS_DAMAGED_RETURN',
                    'LOGISTICS_LOSS',
                    'LOGISTICS_DISCARDED',
                    'LOGISTICS_CLOSURE',
                    'PURCHASE_REQUEST',
                    'PURCHASE_RECEIPT',
                    'PURCHASE_WAREHOUSE_RECEIPT',
                    'PURCHASE_DIRECT_EVENT_DELIVERY',
                    'STOCK_ADJUSTMENT',
                    'STOCK_DAMAGE',
                    'STOCK_LOSS',
                    'STOCK_CORRECTION'
                );
            end if;
        end $$;
        """
    )
    stage_enum = postgresql.ENUM(name="logistics_evidence_stage", create_type=False)
    op.create_table(
        "logistics_evidences",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("events.id", ondelete="SET NULL"), nullable=True),
        sa.Column("logistics_order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("logistics_orders.id", ondelete="CASCADE"), nullable=True),
        sa.Column("logistics_order_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("logistics_order_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("purchase_request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("purchase_requests.id", ondelete="CASCADE"), nullable=True),
        sa.Column("purchase_request_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("purchase_request_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("stock_movement_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stock_movements.id", ondelete="SET NULL"), nullable=True),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True),
        sa.Column("evidence_stage", stage_enum, nullable=False),
        sa.Column("file_url", sa.Text(), nullable=False),
        sa.Column("file_key", sa.Text(), nullable=True),
        sa.Column("file_name", sa.Text(), nullable=True),
        sa.Column("file_type", sa.String(length=80), nullable=True),
        sa.Column("mime_type", sa.String(length=120), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_logistics_evidences_event_id", "logistics_evidences", ["event_id"])
    op.create_index("idx_logistics_evidences_order_id", "logistics_evidences", ["logistics_order_id"])
    op.create_index("idx_logistics_evidences_order_item_id", "logistics_evidences", ["logistics_order_item_id"])
    op.create_index("idx_logistics_evidences_purchase_request_id", "logistics_evidences", ["purchase_request_id"])
    op.create_index("idx_logistics_evidences_purchase_request_item_id", "logistics_evidences", ["purchase_request_item_id"])
    op.create_index("idx_logistics_evidences_stock_movement_id", "logistics_evidences", ["stock_movement_id"])
    op.create_index("idx_logistics_evidences_warehouse_id", "logistics_evidences", ["warehouse_id"])
    op.create_index("idx_logistics_evidences_stage", "logistics_evidences", ["evidence_stage"])

    op.execute("alter table logistics_evidences enable row level security")
    op.execute(
        """
        create policy logistics_evidences_rls on logistics_evidences
        using (
            app_current_role() in ('SUPER_ADMIN', 'ADMIN')
            or (event_id is not null and app_can_view_event(event_id))
            or exists (
                select 1
                from logistics_orders lo
                where lo.id = logistics_evidences.logistics_order_id
                  and lo.assigned_operator_id = app_current_user_id()
            )
            or exists (
                select 1
                from warehouse_users wu
                where wu.warehouse_id = logistics_evidences.warehouse_id
                  and wu.user_id = app_current_user_id()
                  and wu.can_view_stock = true
            )
        )
        with check (
            app_current_role() in ('SUPER_ADMIN', 'ADMIN')
            or exists (
                select 1
                from logistics_orders lo
                where lo.id = logistics_evidences.logistics_order_id
                  and lo.assigned_operator_id = app_current_user_id()
            )
            or exists (
                select 1
                from warehouse_users wu
                where wu.warehouse_id = logistics_evidences.warehouse_id
                  and wu.user_id = app_current_user_id()
                  and wu.can_manage_stock = true
            )
        )
        """
    )


def downgrade() -> None:
    op.execute("drop policy if exists logistics_evidences_rls on logistics_evidences")
    op.drop_index("idx_logistics_evidences_stage", table_name="logistics_evidences")
    op.drop_index("idx_logistics_evidences_warehouse_id", table_name="logistics_evidences")
    op.drop_index("idx_logistics_evidences_stock_movement_id", table_name="logistics_evidences")
    op.drop_index("idx_logistics_evidences_purchase_request_item_id", table_name="logistics_evidences")
    op.drop_index("idx_logistics_evidences_purchase_request_id", table_name="logistics_evidences")
    op.drop_index("idx_logistics_evidences_order_item_id", table_name="logistics_evidences")
    op.drop_index("idx_logistics_evidences_order_id", table_name="logistics_evidences")
    op.drop_index("idx_logistics_evidences_event_id", table_name="logistics_evidences")
    op.drop_table("logistics_evidences")
    op.execute("drop type if exists logistics_evidence_stage")
