"""add logistics closure

Revision ID: 20260629_0023
Revises: 20260629_0022
Create Date: 2026-06-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260629_0023"
down_revision: str | None = "20260629_0022"
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
    _add_enum_value("logistics_order_status", "CLOSED")

    op.add_column("logistics_orders", sa.Column("closed_at", sa.DateTime(), nullable=True))
    op.add_column(
        "logistics_orders",
        sa.Column(
            "closed_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column("logistics_orders", sa.Column("closure_notes", sa.Text(), nullable=True))
    op.create_index("idx_logistics_orders_closed_by", "logistics_orders", ["closed_by"])


def downgrade() -> None:
    op.drop_index("idx_logistics_orders_closed_by", table_name="logistics_orders")
    op.drop_column("logistics_orders", "closure_notes")
    op.drop_column("logistics_orders", "closed_by")
    op.drop_column("logistics_orders", "closed_at")
