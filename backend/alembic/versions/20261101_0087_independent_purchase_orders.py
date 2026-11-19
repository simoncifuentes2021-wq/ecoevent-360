"""Add independent purchase orders, without stock/inventory relations."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261101_0087"
down_revision: str | None = "20261021_0086"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("create sequence purchase_order_number_seq start with 1")
    op.execute("grant usage, select on sequence purchase_order_number_seq to public")
    op.create_table(
        "purchase_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("order_number", sa.String(32), nullable=False, unique=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(24), nullable=False, server_default="'DRAFT'"),
        sa.Column("event_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("events.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_name_snapshot", sa.String(180)),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("supplier_name", sa.String(180), nullable=False),
        sa.Column("supplier_rut", sa.String(30)),
        sa.Column("supplier_email", sa.String(180)),
        sa.Column("supplier_phone", sa.String(50)),
        sa.Column("supplier_address", sa.Text()),
        sa.Column("delivery_address", sa.Text()),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("required_date", sa.Date()),
        sa.Column("payment_terms", sa.String(240)),
        sa.Column("notes", sa.Text()),
        sa.Column("currency", sa.String(3), nullable=False, server_default="'CLP'"),
        sa.Column("subtotal", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("tax_total", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("total", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("sent_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("approved_at", sa.DateTime()),
        sa.Column("sent_at", sa.DateTime()),
        sa.Column("cancelled_at", sa.DateTime()),
        sa.Column("cancellation_reason", sa.Text()),
        sa.Column("pdf_storage_key", sa.Text()),
        sa.Column("pdf_sha256", sa.String(64)),
        sa.Column("pdf_version", sa.Integer()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint(
            "status in ('DRAFT','APPROVED','SENT','PARTIALLY_RECEIVED','RECEIVED','CANCELLED')",
            name="ck_purchase_orders_status",
        ),
        sa.CheckConstraint("subtotal >= 0", name="ck_purchase_orders_subtotal_nonnegative"),
        sa.CheckConstraint("tax_total >= 0", name="ck_purchase_orders_tax_nonnegative"),
        sa.CheckConstraint("total >= 0", name="ck_purchase_orders_total_nonnegative"),
    )
    op.create_index("idx_purchase_orders_event_id", "purchase_orders", ["event_id"])
    op.create_index("idx_purchase_orders_status", "purchase_orders", ["status"])
    op.create_index("idx_purchase_orders_created_at", "purchase_orders", ["created_at"])
    op.create_table(
        "purchase_order_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("purchase_order_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(240), nullable=False),
        sa.Column("unit", sa.String(40), nullable=False, server_default="'unidad'"),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("received_quantity", sa.Numeric(12, 3), nullable=False, server_default="0"),
        sa.Column("unit_price", sa.Numeric(14, 2), nullable=False),
        sa.Column("tax_rate", sa.Numeric(5, 2), nullable=False, server_default="19"),
        sa.Column("line_subtotal", sa.Numeric(14, 2), nullable=False),
        sa.Column("line_tax", sa.Numeric(14, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(14, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint("line_number > 0", name="ck_purchase_order_items_line_positive"),
        sa.CheckConstraint("quantity > 0", name="ck_purchase_order_items_quantity_positive"),
        sa.CheckConstraint("received_quantity >= 0", name="ck_purchase_order_items_received_nonnegative"),
        sa.CheckConstraint("unit_price >= 0", name="ck_purchase_order_items_price_nonnegative"),
        sa.CheckConstraint("tax_rate >= 0 and tax_rate <= 100", name="ck_purchase_order_items_tax_rate"),
        sa.CheckConstraint(
            "line_subtotal >= 0 and line_tax >= 0 and line_total >= 0",
            name="ck_purchase_order_items_totals_nonnegative",
        ),
    )
    op.create_index("idx_purchase_order_items_order_id", "purchase_order_items", ["purchase_order_id"])
    op.execute(
        """
        alter table purchase_orders enable row level security;
        alter table purchase_order_items enable row level security;
        create policy purchase_orders_admin_all on purchase_orders
            for all using (app_is_admin()) with check (app_is_admin());
        create policy purchase_order_items_admin_all on purchase_order_items
            for all using (
                app_is_admin() and exists (
                    select 1 from purchase_orders po where po.id = purchase_order_items.purchase_order_id
                )
            ) with check (
                app_is_admin() and exists (
                    select 1 from purchase_orders po where po.id = purchase_order_items.purchase_order_id
                )
            );
        """
    )


def downgrade() -> None:
    op.execute("drop policy if exists purchase_order_items_admin_all on purchase_order_items")
    op.execute("drop policy if exists purchase_orders_admin_all on purchase_orders")
    op.drop_index("idx_purchase_order_items_order_id", table_name="purchase_order_items")
    op.drop_table("purchase_order_items")
    op.drop_index("idx_purchase_orders_created_at", table_name="purchase_orders")
    op.drop_index("idx_purchase_orders_status", table_name="purchase_orders")
    op.drop_index("idx_purchase_orders_event_id", table_name="purchase_orders")
    op.drop_table("purchase_orders")
    op.execute("drop sequence if exists purchase_order_number_seq")
