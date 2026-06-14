"""fix order rls policies for insert returning

Revision ID: 20260614_0010
Revises: 20260614_0009
Create Date: 2026-06-14
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260614_0010"
down_revision: str | None = "20260614_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        drop policy if exists event_orders_rls on event_orders;
        drop policy if exists event_order_items_rls on event_order_items;
        drop policy if exists order_evidences_rls on order_evidences;

        create policy event_orders_rls on event_orders
            for all
            using (
                app_can_view_event(event_id)
                or assigned_to = app_current_user_id()
            )
            with check (
                app_is_admin()
                or app_can_view_event(event_id)
            );

        create policy event_order_items_rls on event_order_items
            for all
            using (
                exists (
                    select 1
                    from event_orders eo
                    where eo.id = order_id
                      and (
                        app_can_view_event(eo.event_id)
                        or eo.assigned_to = app_current_user_id()
                      )
                )
            )
            with check (
                exists (
                    select 1
                    from event_orders eo
                    where eo.id = order_id
                      and (
                        app_is_admin()
                        or app_can_view_event(eo.event_id)
                      )
                )
            );

        create policy order_evidences_rls on order_evidences
            for all
            using (
                exists (
                    select 1
                    from event_orders eo
                    where eo.id = order_id
                      and (
                        app_can_view_event(eo.event_id)
                        or eo.assigned_to = app_current_user_id()
                      )
                )
                and (
                    app_current_role() <> 'CLIENT'
                    or visible_to_client = true
                )
            )
            with check (
                app_current_role() in ('SUPER_ADMIN', 'ADMIN', 'SUPERVISOR', 'WORKER')
                and exists (
                    select 1
                    from event_orders eo
                    where eo.id = order_id
                      and (
                        app_is_admin()
                        or app_can_view_event(eo.event_id)
                        or eo.assigned_to = app_current_user_id()
                      )
                )
            );
        """
    )


def downgrade() -> None:
    op.execute(
        """
        drop policy if exists order_evidences_rls on order_evidences;
        drop policy if exists event_order_items_rls on event_order_items;
        drop policy if exists event_orders_rls on event_orders;

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
