"""Add approved partial-dispatch order splitting.

Revision ID: 20260904_0060
Revises: 20260904_0059
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260904_0060"
down_revision: str | None = "20260904_0059"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "logistics_orders",
        sa.Column("parent_order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("logistics_orders.id", ondelete="SET NULL")),
    )
    op.create_index("idx_logistics_orders_parent_order_id", "logistics_orders", ["parent_order_id"])
    op.create_table(
        "logistics_partial_dispatch_requests",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("logistics_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("pending_order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("logistics_orders.id", ondelete="SET NULL")),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("review_notes", sa.Text()),
        sa.Column("requested_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("reviewed_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint("status in ('PENDING','APPROVED','REJECTED','CANCELLED')"),
    )
    op.create_index("idx_logistics_partial_dispatch_requests_order_id", "logistics_partial_dispatch_requests", ["order_id"])
    op.create_index("idx_logistics_partial_dispatch_requests_status", "logistics_partial_dispatch_requests", ["status"])


def downgrade() -> None:
    op.drop_table("logistics_partial_dispatch_requests")
    op.drop_index("idx_logistics_orders_parent_order_id", table_name="logistics_orders")
    op.drop_column("logistics_orders", "parent_order_id")
