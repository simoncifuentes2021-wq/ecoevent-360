"""add warehouses module

Revision ID: 20260624_0012
Revises: 20260624_0011
Create Date: 2026-06-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260624_0012"
down_revision: str | None = "20260624_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "warehouses",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("TRUE"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("idx_warehouses_is_active", "warehouses", ["is_active"])
    op.create_index("idx_warehouses_city", "warehouses", ["city"])
    op.execute(
        """
        create unique index uq_warehouses_active_name
        on warehouses (lower(trim(name)))
        where is_active = true
        """
    )

    op.create_table(
        "warehouse_users",
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
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("can_view_stock", sa.Boolean(), server_default=sa.text("TRUE"), nullable=False),
        sa.Column("can_manage_stock", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False),
        sa.Column("can_dispatch_orders", sa.Boolean(), server_default=sa.text("TRUE"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.UniqueConstraint("warehouse_id", "user_id", name="uq_warehouse_users_warehouse_user"),
    )
    op.create_index("idx_warehouse_users_warehouse_id", "warehouse_users", ["warehouse_id"])
    op.create_index("idx_warehouse_users_user_id", "warehouse_users", ["user_id"])

    op.execute(
        """
        alter table warehouses enable row level security;
        alter table warehouse_users enable row level security;

        create policy warehouses_rls on warehouses
            for all
            using (
                app_is_admin()
                or (
                    app_current_role() = 'SUPERVISOR'
                    and is_active = true
                )
                or (
                    app_current_role() = 'LOGISTICS_OPERATOR'
                    and is_active = true
                    and exists (
                        select 1
                        from warehouse_users wu
                        where wu.warehouse_id = warehouses.id
                          and wu.user_id = app_current_user_id()
                    )
                )
            )
            with check (app_is_admin());

        create policy warehouse_users_rls on warehouse_users
            for all
            using (
                app_is_admin()
                or (
                    app_current_role() = 'LOGISTICS_OPERATOR'
                    and user_id = app_current_user_id()
                )
            )
            with check (app_is_admin());
        """
    )


def downgrade() -> None:
    op.execute("drop policy if exists warehouse_users_rls on warehouse_users")
    op.execute("drop policy if exists warehouses_rls on warehouses")
    op.drop_index("idx_warehouse_users_user_id", table_name="warehouse_users")
    op.drop_index("idx_warehouse_users_warehouse_id", table_name="warehouse_users")
    op.drop_table("warehouse_users")
    op.drop_index("uq_warehouses_active_name", table_name="warehouses")
    op.drop_index("idx_warehouses_city", table_name="warehouses")
    op.drop_index("idx_warehouses_is_active", table_name="warehouses")
    op.drop_table("warehouses")
