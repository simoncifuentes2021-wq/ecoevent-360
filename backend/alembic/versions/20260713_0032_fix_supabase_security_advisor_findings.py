"""fix supabase security advisor findings

Revision ID: 20260713_0032
Revises: 20260713_0031
Create Date: 2026-07-13 04:00:00.000000
"""

from alembic import op


revision = "20260713_0032"
down_revision = "20260713_0031"
branch_labels = None
depends_on = None


SECURITY_INVOKER_VIEWS = (
    "event_task_summary",
    "event_incident_summary",
    "event_waste_summary",
    "event_carbon_summary",
    "event_survey_summary",
)

PORTAL_TABLES = (
    "client_portal_configs",
    "client_portal_sections",
    "client_portal_widgets",
)


def upgrade() -> None:
    for view in SECURITY_INVOKER_VIEWS:
        op.execute(f"alter view {view} set (security_invoker = true)")

    op.execute("alter table alembic_version enable row level security")
    op.execute("alter table users enable row level security")

    for table in PORTAL_TABLES:
        op.execute(f"alter table {table} enable row level security")

    op.execute(
        """
        drop policy if exists users_read_rls on users;
        drop policy if exists users_write_rls on users;
        drop policy if exists client_portal_configs_rls on client_portal_configs;
        drop policy if exists client_portal_sections_rls on client_portal_sections;
        drop policy if exists client_portal_widgets_rls on client_portal_widgets;

        create policy users_read_rls on users
            for select
            using (
                app_is_admin()
                or id = app_current_user_id()
                or (
                    app_current_role() = 'SUPERVISOR'
                    and role in ('SUPERVISOR', 'WORKER', 'LOGISTICS_OPERATOR')
                    and is_active = true
                )
            );

        create policy users_write_rls on users
            for all
            using (app_is_admin())
            with check (app_is_admin());

        create policy client_portal_configs_rls on client_portal_configs
            for all
            using (app_can_view_event(event_id))
            with check (app_is_admin() and app_can_access_client(client_id));

        create policy client_portal_sections_rls on client_portal_sections
            for all
            using (
                exists (
                    select 1
                    from client_portal_configs c
                    where c.id = config_id
                      and app_can_view_event(c.event_id)
                )
            )
            with check (
                exists (
                    select 1
                    from client_portal_configs c
                    where c.id = config_id
                      and app_is_admin()
                      and app_can_access_client(c.client_id)
                )
            );

        create policy client_portal_widgets_rls on client_portal_widgets
            for all
            using (
                exists (
                    select 1
                    from client_portal_configs c
                    where c.id = config_id
                      and app_can_view_event(c.event_id)
                )
            )
            with check (
                exists (
                    select 1
                    from client_portal_configs c
                    where c.id = config_id
                      and app_is_admin()
                      and app_can_access_client(c.client_id)
                )
            );
        """
    )

    op.execute(
        """
        do $$
        begin
            if exists (select 1 from pg_roles where rolname = 'anon') then
                revoke all on table alembic_version from anon;
                revoke all on table users from anon;
            end if;

            if exists (select 1 from pg_roles where rolname = 'authenticated') then
                revoke all on table alembic_version from authenticated;
                revoke all on table users from authenticated;
            end if;
        end
        $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        drop policy if exists client_portal_widgets_rls on client_portal_widgets;
        drop policy if exists client_portal_sections_rls on client_portal_sections;
        drop policy if exists client_portal_configs_rls on client_portal_configs;
        drop policy if exists users_write_rls on users;
        drop policy if exists users_read_rls on users;
        """
    )

    for table in PORTAL_TABLES:
        op.execute(f"alter table {table} disable row level security")

    op.execute("alter table users disable row level security")
    op.execute("alter table alembic_version disable row level security")

    for view in SECURITY_INVOKER_VIEWS:
        op.execute(f"alter view {view} set (security_invoker = false)")
