"""enable row level security policies

Revision ID: 20260610_0005
Revises: 20260604_0004
Create Date: 2026-06-10
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260610_0005"
down_revision: str | None = "20260604_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


RLS_TABLES = (
    "clients",
    "events",
    "event_zones",
    "event_services",
    "event_staff",
    "tasks",
    "incidents",
    "evidences",
    "waste_records",
    "carbon_records",
    "fuel_records",
    "energy_records",
    "water_records",
    "surveys",
    "survey_imports",
    "survey_responses",
    "alerts",
    "reports",
    "audit_logs",
)

REFERENCE_TABLES = ("services", "waste_types", "carbon_factors")


def upgrade() -> None:
    op.execute(
        """
        create or replace function app_current_user_id()
        returns uuid
        language sql
        stable
        security definer
        set search_path = public
        as $$
            select nullif(current_setting('app.current_user_id', true), '')::uuid
        $$;

        create or replace function app_current_client_id()
        returns uuid
        language sql
        stable
        security definer
        set search_path = public
        as $$
            select nullif(current_setting('app.current_client_id', true), '')::uuid
        $$;

        create or replace function app_current_role()
        returns text
        language sql
        stable
        security definer
        set search_path = public
        as $$
            select nullif(current_setting('app.current_role', true), '')
        $$;

        create or replace function app_is_admin()
        returns boolean
        language sql
        stable
        security definer
        set search_path = public
        as $$
            select app_current_role() in ('SUPER_ADMIN', 'ADMIN')
        $$;

        create or replace function app_is_authenticated()
        returns boolean
        language sql
        stable
        security definer
        set search_path = public
        as $$
            select app_current_user_id() is not null
        $$;

        create or replace function app_can_access_client(client_uuid uuid)
        returns boolean
        language sql
        stable
        security definer
        set search_path = public
        as $$
            select
                app_is_admin()
                or (
                    app_current_role() = 'CLIENT'
                    and app_current_client_id() = client_uuid
                )
        $$;

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

        create or replace function app_can_manage_reference_data()
        returns boolean
        language sql
        stable
        security definer
        set search_path = public
        as $$
            select app_is_admin()
        $$;
        """
    )

    for table in RLS_TABLES:
        op.execute(f"alter table {table} enable row level security")

    for table in REFERENCE_TABLES:
        op.execute(f"alter table {table} enable row level security")

    op.execute(
        """
        create policy clients_rls on clients
            for all
            using (app_is_admin() or (app_current_role() = 'CLIENT' and id = app_current_client_id()))
            with check (app_is_admin() or (app_current_role() = 'CLIENT' and id = app_current_client_id()));

        create policy events_rls on events
            for all
            using (app_can_view_event(id))
            with check (app_is_admin() or app_can_access_client(client_id));

        create policy event_zones_rls on event_zones
            for all
            using (app_can_view_event(event_id))
            with check (app_can_view_event(event_id));

        create policy event_services_rls on event_services
            for all
            using (app_can_view_event(event_id))
            with check (app_can_view_event(event_id));

        create policy event_staff_rls on event_staff
            for all
            using (app_can_view_event(event_id) or user_id = app_current_user_id())
            with check (app_can_view_event(event_id));

        create policy tasks_rls on tasks
            for all
            using (app_can_view_event(event_id) or assigned_to = app_current_user_id())
            with check (app_can_view_event(event_id));

        create policy incidents_rls on incidents
            for all
            using (
                app_can_view_event(event_id)
                or reported_by = app_current_user_id()
                or assigned_to = app_current_user_id()
            )
            with check (app_can_view_event(event_id));

        create policy evidences_rls on evidences
            for all
            using (app_can_view_event(event_id) or uploaded_by = app_current_user_id())
            with check (app_can_view_event(event_id) or uploaded_by = app_current_user_id());

        create policy waste_records_rls on waste_records
            for all
            using (app_can_view_event(event_id) or recorded_by = app_current_user_id())
            with check (app_can_view_event(event_id) or recorded_by = app_current_user_id());

        create policy carbon_records_rls on carbon_records
            for all
            using (app_can_view_event(event_id) or recorded_by = app_current_user_id())
            with check (app_can_view_event(event_id) or recorded_by = app_current_user_id());

        create policy fuel_records_rls on fuel_records
            for all
            using (app_can_view_event(event_id) or recorded_by = app_current_user_id())
            with check (app_can_view_event(event_id) or recorded_by = app_current_user_id());

        create policy energy_records_rls on energy_records
            for all
            using (app_can_view_event(event_id) or recorded_by = app_current_user_id())
            with check (app_can_view_event(event_id) or recorded_by = app_current_user_id());

        create policy water_records_rls on water_records
            for all
            using (app_can_view_event(event_id) or recorded_by = app_current_user_id())
            with check (app_can_view_event(event_id) or recorded_by = app_current_user_id());

        create policy surveys_rls on surveys
            for all
            using (app_can_view_event(event_id))
            with check (app_can_view_event(event_id));

        create policy survey_imports_rls on survey_imports
            for all
            using (
                exists (
                    select 1
                    from surveys s
                    where s.id = survey_id
                      and app_can_view_event(s.event_id)
                )
            )
            with check (
                exists (
                    select 1
                    from surveys s
                    where s.id = survey_id
                      and app_can_view_event(s.event_id)
                )
            );

        create policy survey_responses_rls on survey_responses
            for all
            using (app_can_view_event(event_id))
            with check (app_can_view_event(event_id));

        create policy alerts_rls on alerts
            for all
            using (app_can_view_event(event_id))
            with check (app_can_view_event(event_id));

        create policy reports_rls on reports
            for all
            using (app_can_view_event(event_id))
            with check (app_can_view_event(event_id));

        create policy audit_logs_rls on audit_logs
            for all
            using (
                app_is_admin()
                or user_id = app_current_user_id()
                or (client_id is not null and app_can_access_client(client_id))
                or (event_id is not null and app_can_view_event(event_id))
            )
            with check (app_is_authenticated());

        create policy services_read_rls on services
            for select
            using (app_is_authenticated());

        create policy services_write_rls on services
            for all
            using (app_can_manage_reference_data())
            with check (app_can_manage_reference_data());

        create policy waste_types_read_rls on waste_types
            for select
            using (app_is_authenticated());

        create policy waste_types_write_rls on waste_types
            for all
            using (app_can_manage_reference_data())
            with check (app_can_manage_reference_data());

        create policy carbon_factors_read_rls on carbon_factors
            for select
            using (app_is_authenticated());

        create policy carbon_factors_write_rls on carbon_factors
            for all
            using (app_can_manage_reference_data())
            with check (app_can_manage_reference_data());
        """
    )


def downgrade() -> None:
    for table in (*RLS_TABLES, *REFERENCE_TABLES):
        op.execute(f"alter table {table} disable row level security")

    op.execute(
        """
        drop function if exists app_can_manage_reference_data();
        drop function if exists app_can_view_event(uuid);
        drop function if exists app_can_access_client(uuid);
        drop function if exists app_is_authenticated();
        drop function if exists app_is_admin();
        drop function if exists app_current_role();
        drop function if exists app_current_client_id();
        drop function if exists app_current_user_id();
        """
    )
