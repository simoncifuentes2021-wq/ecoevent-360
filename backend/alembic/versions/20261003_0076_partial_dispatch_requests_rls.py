"""Protect partial dispatch requests with event and order scoped RLS.

Revision ID: 20261003_0076
Revises: 20261003_0075
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20261003_0076"
down_revision: str | None = "20261003_0075"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        alter table logistics_partial_dispatch_requests enable row level security;

        create policy logistics_partial_dispatch_requests_select
            on logistics_partial_dispatch_requests for select
            using (
                app_is_admin()
                or exists (
                    select 1 from logistics_orders lo
                    where lo.id = logistics_partial_dispatch_requests.order_id
                      and (
                          (app_current_role() = 'SUPERVISOR'
                           and app_can_view_event(lo.event_id))
                          or (app_current_role() = 'LOGISTICS_OPERATOR'
                              and lo.assigned_operator_id = app_current_user_id())
                      )
                )
            );

        create policy logistics_partial_dispatch_requests_insert
            on logistics_partial_dispatch_requests for insert
            with check (
                requested_by = app_current_user_id()
                and status = 'PENDING'
                and reviewed_by is null
                and pending_order_id is null
                and (
                    app_is_admin()
                    or exists (
                        select 1 from logistics_orders lo
                        where lo.id = logistics_partial_dispatch_requests.order_id
                          and (
                              (app_current_role() = 'SUPERVISOR'
                               and app_can_view_event(lo.event_id))
                              or (app_current_role() = 'LOGISTICS_OPERATOR'
                                  and lo.assigned_operator_id = app_current_user_id())
                          )
                    )
                )
            );

        create policy logistics_partial_dispatch_requests_update
            on logistics_partial_dispatch_requests for update
            using (
                app_is_admin()
                or exists (
                    select 1 from logistics_orders lo
                    where lo.id = logistics_partial_dispatch_requests.order_id
                      and app_current_role() = 'SUPERVISOR'
                      and app_can_view_event(lo.event_id)
                )
            )
            with check (
                app_is_admin()
                or exists (
                    select 1 from logistics_orders lo
                    where lo.id = logistics_partial_dispatch_requests.order_id
                      and app_current_role() = 'SUPERVISOR'
                      and app_can_view_event(lo.event_id)
                )
            );

        create policy logistics_partial_dispatch_requests_delete
            on logistics_partial_dispatch_requests for delete
            using (app_is_admin());
        """
    )


def downgrade() -> None:
    op.execute(
        """
        drop policy if exists logistics_partial_dispatch_requests_delete
            on logistics_partial_dispatch_requests;
        drop policy if exists logistics_partial_dispatch_requests_update
            on logistics_partial_dispatch_requests;
        drop policy if exists logistics_partial_dispatch_requests_insert
            on logistics_partial_dispatch_requests;
        drop policy if exists logistics_partial_dispatch_requests_select
            on logistics_partial_dispatch_requests;
        alter table logistics_partial_dispatch_requests disable row level security;
        """
    )
