"""add inventory items

Revision ID: 20260624_0013
Revises: 20260624_0012
Create Date: 2026-06-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260624_0013"
down_revision: str | None = "20260624_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        do $$
        begin
            if not exists (select 1 from pg_type where typname = 'inventory_item_type') then
                create type inventory_item_type as enum (
                    'RETURNABLE',
                    'CONSUMABLE',
                    'PARTIAL_CONSUMABLE',
                    'DISPOSABLE'
                );
            end if;
        end $$;
        """
    )
    inventory_item_type = postgresql.ENUM(name="inventory_item_type", create_type=False)

    op.create_table(
        "inventory_items",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("sku", sa.String(length=80), nullable=True),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("item_type", inventory_item_type, nullable=False),
        sa.Column("return_required", sa.Boolean(), server_default=sa.text("TRUE"), nullable=False),
        sa.Column("unit", sa.String(length=50), nullable=True),
        sa.Column("replacement_cost", sa.Numeric(12, 2), nullable=True),
        sa.Column("min_stock", sa.Numeric(12, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("TRUE"), nullable=False),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.CheckConstraint("replacement_cost >= 0", name="ck_inventory_items_replacement_cost_non_negative"),
        sa.CheckConstraint("min_stock >= 0", name="ck_inventory_items_min_stock_non_negative"),
        sa.CheckConstraint(
            """
            (
                item_type = 'RETURNABLE' and return_required = true
            )
            or (
                item_type in ('CONSUMABLE', 'DISPOSABLE') and return_required = false
            )
            or item_type = 'PARTIAL_CONSUMABLE'
            """,
            name="ck_inventory_items_return_required_by_type",
        ),
    )
    op.create_index("idx_inventory_items_sku", "inventory_items", ["sku"])
    op.create_index("idx_inventory_items_item_type", "inventory_items", ["item_type"])
    op.create_index("idx_inventory_items_is_active", "inventory_items", ["is_active"])
    op.execute(
        """
        create unique index uq_inventory_items_active_name
        on inventory_items (lower(trim(name)))
        where is_active = true
        """
    )

    op.execute(
        """
        alter table inventory_items enable row level security;

        create policy inventory_items_rls on inventory_items
            for all
            using (
                app_is_admin()
                or app_current_role() = 'LOGISTICS_OPERATOR'
                or (
                    app_current_role() = 'SUPERVISOR'
                    and is_active = true
                )
            )
            with check (
                app_is_admin()
                or app_current_role() = 'LOGISTICS_OPERATOR'
            );
        """
    )


def downgrade() -> None:
    op.execute("drop policy if exists inventory_items_rls on inventory_items")
    op.drop_index("uq_inventory_items_active_name", table_name="inventory_items")
    op.drop_index("idx_inventory_items_is_active", table_name="inventory_items")
    op.drop_index("idx_inventory_items_item_type", table_name="inventory_items")
    op.drop_index("idx_inventory_items_sku", table_name="inventory_items")
    op.drop_table("inventory_items")
    op.execute("drop type if exists inventory_item_type")
