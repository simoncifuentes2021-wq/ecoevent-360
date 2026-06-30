"""add logistics operator role

Revision ID: 20260624_0011
Revises: 20260614_0010
Create Date: 2026-06-24
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260624_0011"
down_revision: str | None = "20260614_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        do $$
        begin
            if not exists (
                select 1
                from pg_enum e
                join pg_type t on t.oid = e.enumtypid
                where t.typname = 'user_role'
                  and e.enumlabel = 'LOGISTICS_OPERATOR'
            ) then
                alter type user_role add value 'LOGISTICS_OPERATOR';
            end if;
        end $$;
        """
    )
    op.execute(
        """
        create or replace function app_can_view_event(event_uuid uuid)
        returns boolean
        language sql
        stable
        security definer
        set search_path = public
        as $$
            select exists (
                select 1
                from events e
                where e.id = event_uuid
                  and (
                    app_is_admin()
                    or (
                        app_current_role() = 'CLIENT'
                        and app_current_client_id() = e.client_id
                    )
                    or (
                        app_current_role() in ('SUPERVISOR', 'WORKER', 'LOGISTICS_OPERATOR')
                        and e.status <> 'QUOTE'
                        and e.hidden_from_operations = false
                        and (
                            exists (
                                select 1
                                from event_staff es
                                where es.event_id = e.id
                                  and es.user_id = app_current_user_id()
                            )
                            or exists (
                                select 1
                                from tasks t
                                where t.event_id = e.id
                                  and t.assigned_to = app_current_user_id()
                            )
                        )
                    )
                  )
            )
        $$;

        create or replace function app_can_view_order(order_uuid uuid)
        returns boolean
        language sql
        stable
        security definer
        set search_path = public
        as $$
            select exists (
                select 1
                from event_orders eo
                left join events e on e.id = eo.event_id
                where eo.id = order_uuid
                  and (
                    app_is_admin()
                    or (
                        app_current_role() = 'CLIENT'
                        and app_current_client_id() = e.client_id
                    )
                    or (
                        app_current_role() = 'SUPERVISOR'
                        and app_can_view_event(eo.event_id)
                    )
                    or (
                        app_current_role() = 'LOGISTICS_OPERATOR'
                        and eo.assigned_to = app_current_user_id()
                    )
                  )
            )
        $$;

        drop policy if exists catalog_items_rls on catalog_items;
        drop policy if exists event_orders_rls on event_orders;
        drop policy if exists event_order_items_rls on event_order_items;
        drop policy if exists order_evidences_rls on order_evidences;

        create policy catalog_items_rls on catalog_items
            for all
            using (app_current_role() in ('SUPER_ADMIN', 'ADMIN', 'SUPERVISOR', 'LOGISTICS_OPERATOR'))
            with check (app_is_admin());

        create policy event_orders_rls on event_orders
            for all
            using (app_can_view_order(id))
            with check (
                app_is_admin()
                or (
                    app_current_role() = 'SUPERVISOR'
                    and app_can_view_event(event_id)
                )
                or (
                    app_current_role() = 'LOGISTICS_OPERATOR'
                    and assigned_to = app_current_user_id()
                )
            );

        create policy event_order_items_rls on event_order_items
            for all
            using (app_can_view_order(order_id))
            with check (
                exists (
                    select 1
                    from event_orders eo
                    where eo.id = order_id
                      and (
                        app_is_admin()
                        or (
                            app_current_role() = 'SUPERVISOR'
                            and app_can_view_event(eo.event_id)
                        )
                        or (
                            app_current_role() = 'LOGISTICS_OPERATOR'
                            and eo.assigned_to = app_current_user_id()
                        )
                      )
                )
            );

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
                app_current_role() in ('SUPER_ADMIN', 'ADMIN', 'SUPERVISOR', 'LOGISTICS_OPERATOR')
                and app_can_view_order(order_id)
            );
        """
    )


def downgrade() -> None:
    op.execute(
        """
        drop policy if exists order_evidences_rls on order_evidences;
        drop policy if exists event_order_items_rls on event_order_items;
        drop policy if exists event_orders_rls on event_orders;
        drop policy if exists catalog_items_rls on catalog_items;

        create or replace function app_can_view_event(event_uuid uuid)
        returns boolean
        language sql
        stable
        security definer
        set search_path = public
        as $$
            select exists (
                select 1
                from events e
                where e.id = event_uuid
                  and (
                    app_is_admin()
                    or (
                        app_current_role() = 'CLIENT'
                        and app_current_client_id() = e.client_id
                    )
                    or (
                        app_current_role() in ('SUPERVISOR', 'WORKER')
                        and e.status <> 'QUOTE'
                        and e.hidden_from_operations = false
                        and (
                            exists (
                                select 1
                                from event_staff es
                                where es.event_id = e.id
                                  and es.user_id = app_current_user_id()
                            )
                            or exists (
                                select 1
                                from tasks t
                                where t.event_id = e.id
                                  and t.assigned_to = app_current_user_id()
                            )
                        )
                    )
                  )
            )
        $$;

        create or replace function app_can_view_order(order_uuid uuid)
        returns boolean
        language sql
        stable
        security definer
        set search_path = public
        as $$
            select exists (
                select 1
                from event_orders eo
                where eo.id = order_uuid
                  and (
                    app_can_view_event(eo.event_id)
                    or eo.assigned_to = app_current_user_id()
                  )
            )
        $$;

        create policy catalog_items_rls on catalog_items
            for all
            using (app_current_role() in ('SUPER_ADMIN', 'ADMIN', 'SUPERVISOR', 'WORKER'))
            with check (app_is_admin());

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
