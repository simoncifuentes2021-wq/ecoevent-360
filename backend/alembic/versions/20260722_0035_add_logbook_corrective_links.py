"""add logbook corrective links

Revision ID: 20260722_0035
Revises: 20260722_0034
"""

from alembic import op

revision = "20260722_0035"
down_revision = "20260722_0034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    create table logbook_incident_links(
      id uuid primary key default uuid_generate_v4(), incident_id uuid not null references incidents(id) on delete restrict,
      instance_id uuid not null references logbook_instances(id) on delete restrict, assignment_id uuid not null references logbook_assignments(id) on delete restrict,
      item_id uuid not null references logbook_items(id) on delete restrict, response_id uuid not null references logbook_responses(id) on delete restrict,
      worker_id uuid references users(id) on delete set null, created_by uuid references users(id) on delete set null,
      created_at timestamp not null default now(), constraint uq_logbook_incident_response unique(response_id));
    create table logbook_task_links(
      id uuid primary key default uuid_generate_v4(), task_id uuid not null references tasks(id) on delete restrict,
      instance_id uuid not null references logbook_instances(id) on delete restrict, assignment_id uuid not null references logbook_assignments(id) on delete restrict,
      item_id uuid not null references logbook_items(id) on delete restrict, response_id uuid not null references logbook_responses(id) on delete restrict,
      created_by uuid references users(id) on delete set null, created_at timestamp not null default now(),
      constraint uq_logbook_task_response unique(response_id));
    create table logbook_corrective_evidence_links(
      id uuid primary key default uuid_generate_v4(), logbook_evidence_id uuid not null references logbook_evidences(id) on delete restrict,
      incident_link_id uuid references logbook_incident_links(id) on delete cascade, task_link_id uuid references logbook_task_links(id) on delete cascade,
      created_at timestamp not null default now(), check((incident_link_id is not null) <> (task_link_id is not null)));
    """)
    op.execute("""
    create policy logbook_templates_authenticated_read on logbook_templates for select
      using (app_current_user_id() is not null and (status='ACTIVE' or app_current_role() in ('SUPERVISOR','ADMIN','SUPER_ADMIN')));
    create policy logbook_versions_authenticated_read on logbook_template_versions for select
      using (app_current_user_id() is not null and (status='PUBLISHED' or app_current_role() in ('ADMIN','SUPER_ADMIN')));
    create policy logbook_sections_authenticated_read on logbook_sections for select
      using (exists(select 1 from logbook_template_versions v where v.id=template_version_id and (v.status='PUBLISHED' or app_is_admin())));
    create policy logbook_items_authenticated_read on logbook_items for select
      using (exists(select 1 from logbook_sections s join logbook_template_versions v on v.id=s.template_version_id where s.id=section_id and (v.status='PUBLISHED' or app_is_admin())));
    create policy logbook_item_options_authenticated_read on logbook_item_options for select
      using (exists(select 1 from logbook_items i join logbook_sections s on s.id=i.section_id join logbook_template_versions v on v.id=s.template_version_id where i.id=logbook_item_id and (v.status='PUBLISHED' or app_is_admin())));
    create policy logbook_assignments_event_supervisor_read on logbook_assignments for select
      using (app_current_role()='SUPERVISOR' and exists(select 1 from logbook_instances li join event_staff es on es.event_id=li.event_id where li.id=logbook_instance_id and es.user_id=app_current_user_id()));
    create policy logbook_assignments_event_supervisor_update on logbook_assignments for update
      using (app_current_role()='SUPERVISOR' and exists(select 1 from logbook_instances li join event_staff es on es.event_id=li.event_id where li.id=logbook_instance_id and es.user_id=app_current_user_id()))
      with check (app_current_role()='SUPERVISOR' and exists(select 1 from logbook_instances li join event_staff es on es.event_id=li.event_id where li.id=logbook_instance_id and es.user_id=app_current_user_id()));
    create policy logbook_responses_event_supervisor_read on logbook_responses for select
      using (app_current_role()='SUPERVISOR' and exists(select 1 from logbook_assignments a join logbook_instances li on li.id=a.logbook_instance_id join event_staff es on es.event_id=li.event_id where a.id=assignment_id and es.user_id=app_current_user_id()));
    create policy logbook_evidences_event_access on logbook_evidences for select
      using (exists(select 1 from logbook_instances li where li.id=instance_id and ((app_current_role()='SUPERVISOR' and exists(select 1 from event_staff es where es.event_id=li.event_id and es.user_id=app_current_user_id())) or (app_current_role()='CLIENT' and li.client_visibility and client_visible and exists(select 1 from events e where e.id=li.event_id and e.client_id=app_current_client_id())))));
    create policy logbook_review_history_event_supervisor_read on logbook_review_history for select
      using (app_current_role()='SUPERVISOR' and exists(select 1 from logbook_assignments a join logbook_instances li on li.id=a.logbook_instance_id join event_staff es on es.event_id=li.event_id where a.id=assignment_id and es.user_id=app_current_user_id()));
    create policy logbook_evidences_participant_all on logbook_evidences for all
      using (exists(select 1 from logbook_assignments a where a.id=assignment_id and a.user_id=app_current_user_id()))
      with check (exists(select 1 from logbook_assignments a where a.id=assignment_id and a.user_id=app_current_user_id()));
    create policy logbook_review_history_participant_read on logbook_review_history for select
      using (exists(select 1 from logbook_assignments a where a.id=assignment_id and a.user_id=app_current_user_id()));
    create policy logbook_review_history_participant_insert on logbook_review_history for insert
      with check (actor_id=app_current_user_id() and exists(select 1 from logbook_assignments a where a.id=assignment_id and a.user_id=app_current_user_id()));
    """)
    for table in (
        "logbook_incident_links",
        "logbook_task_links",
        "logbook_corrective_evidence_links",
    ):
        op.execute(f"alter table {table} enable row level security")
        op.execute(
            f"create policy {table}_admin_all on {table} for all using (app_is_admin()) with check (app_is_admin())"
        )
    op.execute("""
    create policy logbook_incident_links_supervisor on logbook_incident_links for all
      using (app_current_role()='SUPERVISOR' and exists(select 1 from logbook_instances li join event_staff es on es.event_id=li.event_id where li.id=instance_id and es.user_id=app_current_user_id()))
      with check (app_current_role()='SUPERVISOR' and exists(select 1 from logbook_instances li join event_staff es on es.event_id=li.event_id where li.id=instance_id and es.user_id=app_current_user_id()));
    create policy logbook_task_links_supervisor on logbook_task_links for all
      using (app_current_role()='SUPERVISOR' and exists(select 1 from logbook_instances li join event_staff es on es.event_id=li.event_id where li.id=instance_id and es.user_id=app_current_user_id()))
      with check (app_current_role()='SUPERVISOR' and exists(select 1 from logbook_instances li join event_staff es on es.event_id=li.event_id where li.id=instance_id and es.user_id=app_current_user_id()));
    """)


def downgrade() -> None:
    for table, policy in (
        ("logbook_templates", "logbook_templates_authenticated_read"),
        ("logbook_template_versions", "logbook_versions_authenticated_read"),
        ("logbook_sections", "logbook_sections_authenticated_read"),
        ("logbook_items", "logbook_items_authenticated_read"),
        ("logbook_item_options", "logbook_item_options_authenticated_read"),
        ("logbook_assignments", "logbook_assignments_event_supervisor_read"),
        ("logbook_assignments", "logbook_assignments_event_supervisor_update"),
        ("logbook_responses", "logbook_responses_event_supervisor_read"),
        ("logbook_evidences", "logbook_evidences_event_access"),
        ("logbook_evidences", "logbook_evidences_participant_all"),
        ("logbook_review_history", "logbook_review_history_event_supervisor_read"),
        ("logbook_review_history", "logbook_review_history_participant_read"),
        ("logbook_review_history", "logbook_review_history_participant_insert"),
    ):
        op.execute(f"drop policy if exists {policy} on {table}")
    op.execute("drop table if exists logbook_corrective_evidence_links")
    op.execute("drop table if exists logbook_task_links")
    op.execute("drop table if exists logbook_incident_links")
