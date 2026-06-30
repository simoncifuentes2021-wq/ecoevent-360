"""add logistics outcomes

Revision ID: 20260629_0022
Revises: 20260629_0021
Create Date: 2026-06-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260629_0022"
down_revision: str | None = "20260629_0021"
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
    for value in ("OUTCOME_PENDING", "OUTCOME_RECORDED", "WITH_DIFFERENCES"):
        _add_enum_value("logistics_order_status", value)

    op.add_column("logistics_orders", sa.Column("outcome_recorded_at", sa.DateTime(), nullable=True))
    op.add_column(
        "logistics_orders",
        sa.Column(
            "outcome_recorded_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column("logistics_orders", sa.Column("outcome_notes", sa.Text(), nullable=True))
    op.create_index("idx_logistics_orders_outcome_recorded_by", "logistics_orders", ["outcome_recorded_by"])

    op.add_column(
        "logistics_order_items",
        sa.Column("quantity_consumed", sa.Numeric(12, 2), server_default=sa.text("0"), nullable=False),
    )
    op.add_column(
        "logistics_order_items",
        sa.Column("quantity_returned", sa.Numeric(12, 2), server_default=sa.text("0"), nullable=False),
    )
    op.add_column(
        "logistics_order_items",
        sa.Column("quantity_returned_damaged", sa.Numeric(12, 2), server_default=sa.text("0"), nullable=False),
    )
    op.add_column(
        "logistics_order_items",
        sa.Column("quantity_lost", sa.Numeric(12, 2), server_default=sa.text("0"), nullable=False),
    )
    op.add_column(
        "logistics_order_items",
        sa.Column("quantity_discarded", sa.Numeric(12, 2), server_default=sa.text("0"), nullable=False),
    )
    op.add_column(
        "logistics_order_items",
        sa.Column("outcome_status", sa.String(length=40), server_default="PENDING", nullable=False),
    )
    op.add_column("logistics_order_items", sa.Column("outcome_notes", sa.Text(), nullable=True))
    for column in (
        "quantity_consumed",
        "quantity_returned",
        "quantity_returned_damaged",
        "quantity_lost",
        "quantity_discarded",
    ):
        op.create_check_constraint(
            f"ck_logistics_order_items_{column}_non_negative",
            "logistics_order_items",
            f"{column} >= 0",
        )
    op.create_check_constraint(
        "ck_logistics_order_items_outcome_lte_delivered",
        "logistics_order_items",
        "(quantity_consumed + quantity_returned + quantity_returned_damaged + quantity_lost + quantity_discarded) <= quantity_delivered",
    )


def downgrade() -> None:
    op.drop_constraint("ck_logistics_order_items_outcome_lte_delivered", "logistics_order_items", type_="check")
    for column in (
        "quantity_discarded",
        "quantity_lost",
        "quantity_returned_damaged",
        "quantity_returned",
        "quantity_consumed",
    ):
        op.drop_constraint(f"ck_logistics_order_items_{column}_non_negative", "logistics_order_items", type_="check")
    op.drop_column("logistics_order_items", "outcome_notes")
    op.drop_column("logistics_order_items", "outcome_status")
    op.drop_column("logistics_order_items", "quantity_discarded")
    op.drop_column("logistics_order_items", "quantity_lost")
    op.drop_column("logistics_order_items", "quantity_returned_damaged")
    op.drop_column("logistics_order_items", "quantity_returned")
    op.drop_column("logistics_order_items", "quantity_consumed")
    op.drop_index("idx_logistics_orders_outcome_recorded_by", table_name="logistics_orders")
    op.drop_column("logistics_orders", "outcome_notes")
    op.drop_column("logistics_orders", "outcome_recorded_by")
    op.drop_column("logistics_orders", "outcome_recorded_at")
