"""fix logistics order rls for operator workflows

Revision ID: 20260630_0024
Revises: 20260629_0023
Create Date: 2026-06-30
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260630_0024"
down_revision: str | None = "20260629_0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        drop policy if exists logistics_orders_rls on logistics_orders;
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
                or (
                    app_current_role() = 'LOGISTICS_OPERATOR'
                    and assigned_operator_id = app_current_user_id()
                )
            );

        drop policy if exists stock_balances_rls on stock_balances;
        create policy stock_balances_rls on stock_balances
            for all
            using (
                app_is_admin()
                or app_current_role() = 'SUPERVISOR'
                or (
                    app_current_role() = 'LOGISTICS_OPERATOR'
                    and exists (
                        select 1
                        from warehouse_users wu
                        where wu.warehouse_id = stock_balances.warehouse_id
                          and wu.user_id = app_current_user_id()
                          and wu.can_view_stock = true
                    )
                )
            )
            with check (
                app_is_admin()
                or (
                    app_current_role() = 'LOGISTICS_OPERATOR'
                    and exists (
                        select 1
                        from warehouse_users wu
                        where wu.warehouse_id = stock_balances.warehouse_id
                          and wu.user_id = app_current_user_id()
                          and (
                              wu.can_manage_stock = true
                              or wu.can_dispatch_orders = true
                          )
                    )
                )
            );

        drop policy if exists stock_movements_rls on stock_movements;
        create policy stock_movements_rls on stock_movements
            for all
            using (
                app_is_admin()
                or app_current_role() = 'SUPERVISOR'
                or (
                    app_current_role() = 'LOGISTICS_OPERATOR'
                    and exists (
                        select 1
                        from warehouse_users wu
                        where wu.warehouse_id = stock_movements.warehouse_id
                          and wu.user_id = app_current_user_id()
                          and wu.can_view_stock = true
                    )
                )
            )
            with check (
                app_is_admin()
                or (
                    app_current_role() = 'LOGISTICS_OPERATOR'
                    and exists (
                        select 1
                        from warehouse_users wu
                        where wu.warehouse_id = stock_movements.warehouse_id
                          and wu.user_id = app_current_user_id()
                          and (
                              wu.can_manage_stock = true
                              or wu.can_dispatch_orders = true
                          )
                    )
                )
            );
        """
    )


def downgrade() -> None:
    op.execute(
        """
        drop policy if exists logistics_orders_rls on logistics_orders;
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

        drop policy if exists stock_balances_rls on stock_balances;
        create policy stock_balances_rls on stock_balances
            for all
            using (
                app_is_admin()
                or app_current_role() = 'SUPERVISOR'
                or (
                    app_current_role() = 'LOGISTICS_OPERATOR'
                    and exists (
                        select 1
                        from warehouse_users wu
                        where wu.warehouse_id = stock_balances.warehouse_id
                          and wu.user_id = app_current_user_id()
                          and wu.can_view_stock = true
                    )
                )
            )
            with check (
                app_is_admin()
                or (
                    app_current_role() = 'LOGISTICS_OPERATOR'
                    and exists (
                        select 1
                        from warehouse_users wu
                        where wu.warehouse_id = stock_balances.warehouse_id
                          and wu.user_id = app_current_user_id()
                          and wu.can_manage_stock = true
                    )
                )
            );

        drop policy if exists stock_movements_rls on stock_movements;
        create policy stock_movements_rls on stock_movements
            for all
            using (
                app_is_admin()
                or app_current_role() = 'SUPERVISOR'
                or (
                    app_current_role() = 'LOGISTICS_OPERATOR'
                    and exists (
                        select 1
                        from warehouse_users wu
                        where wu.warehouse_id = stock_movements.warehouse_id
                          and wu.user_id = app_current_user_id()
                          and wu.can_view_stock = true
                    )
                )
            )
            with check (
                app_is_admin()
                or (
                    app_current_role() = 'LOGISTICS_OPERATOR'
                    and exists (
                        select 1
                        from warehouse_users wu
                        where wu.warehouse_id = stock_movements.warehouse_id
                          and wu.user_id = app_current_user_id()
                          and wu.can_manage_stock = true
                    )
                )
            );
        """
    )
