"""add event logbooks
Revision ID: 20260722_0034
Revises: 20260713_0033
"""

from alembic import op

revision = "20260722_0034"
down_revision = "20260713_0033"
branch_labels = None
depends_on = None

ENUMS = {
    "logbook_operational_stage": "'SETUP','OPENING','OPERATION','CLOSING','DISMANTLING','OTHER'",
    "logbook_template_status": "'DRAFT','ACTIVE','ARCHIVED'",
    "logbook_version_status": "'DRAFT','PUBLISHED','RETIRED'",
    "logbook_assignment_mode": "'INDIVIDUAL','SHARED'",
    "logbook_item_type": "'CHECKBOX','YES_NO','STATUS_SELECT','NUMBER','SHORT_TEXT','LONG_TEXT','PHOTO','CONFIRMATION'",
    "logbook_evidence_policy": "'NONE','OPTIONAL','REQUIRED','REQUIRED_ON_FAILURE'",
    "logbook_instance_status": "'DRAFT','SCHEDULED','OPEN','IN_PROGRESS','UNDER_REVIEW','CHANGES_REQUESTED','COMPLETED','OVERDUE','CANCELLED'",
    "logbook_assignment_status": "'PENDING','IN_PROGRESS','SUBMITTED','CHANGES_REQUESTED','RESUBMITTED','APPROVED','REJECTED','OVERDUE','CANCELLED'",
    "logbook_result_status": "'PENDING','COMPLETED','FAILED','NOT_APPLICABLE'",
}


def upgrade():
    for n, v in ENUMS.items():
        op.execute(f"create type {n} as enum ({v})")
    op.execute("""
create table logbook_templates(id uuid primary key default uuid_generate_v4(),name varchar(180) not null,description text,instructions text,operational_stage logbook_operational_stage not null,status logbook_template_status not null default 'DRAFT',default_assignment_mode logbook_assignment_mode not null,default_client_visibility boolean not null default false,created_by uuid references users(id) on delete set null,created_at timestamp not null default now(),updated_at timestamp not null default now(),archived_at timestamp);
create index idx_logbook_templates_status on logbook_templates(status);
create table logbook_template_versions(id uuid primary key default uuid_generate_v4(),template_id uuid not null references logbook_templates(id) on delete restrict,version_number integer not null,status logbook_version_status not null default 'DRAFT',change_notes text,created_by uuid references users(id) on delete set null,created_at timestamp not null default now(),published_by uuid references users(id) on delete set null,published_at timestamp,constraint uq_logbook_template_version unique(template_id,version_number));
create table logbook_sections(id uuid primary key default uuid_generate_v4(),template_version_id uuid not null references logbook_template_versions(id) on delete cascade,title varchar(180) not null,description text,position integer not null check(position>=0),is_required boolean not null default true,created_at timestamp not null default now(),constraint uq_logbook_section_position unique(template_version_id,position));
create table logbook_items(id uuid primary key default uuid_generate_v4(),section_id uuid not null references logbook_sections(id) on delete cascade,title varchar(180) not null,description text,instructions text,position integer not null,item_type logbook_item_type not null,is_required boolean not null default true,allow_not_applicable boolean not null default false,evidence_policy logbook_evidence_policy not null default 'NONE',min_evidences integer not null default 0,max_evidences integer not null default 5,require_comment_on_failure boolean not null default false,requires_supervisor_review boolean not null default false,client_visible_by_default boolean not null default false,creates_incident_suggestion boolean not null default false,created_at timestamp not null default now(),constraint uq_logbook_item_position unique(section_id,position),check(min_evidences>=0 and max_evidences>=min_evidences and max_evidences<=10));
create table logbook_item_options(id uuid primary key default uuid_generate_v4(),logbook_item_id uuid not null references logbook_items(id) on delete cascade,label varchar(120) not null,value varchar(80) not null,position integer not null,is_success_value boolean not null default false,is_failure_value boolean not null default false,constraint uq_logbook_item_option_value unique(logbook_item_id,value));
create table logbook_instances(id uuid primary key default uuid_generate_v4(),event_id uuid not null references events(id) on delete restrict,template_id uuid not null references logbook_templates(id) on delete restrict,template_version_id uuid not null references logbook_template_versions(id) on delete restrict,name varchar(180) not null,operational_stage logbook_operational_stage not null,zone_id uuid references event_zones(id) on delete set null,assignment_mode logbook_assignment_mode not null,opens_at timestamp,due_at timestamp,supervisor_id uuid references users(id) on delete set null,status logbook_instance_status not null,client_visibility boolean not null default false,created_by uuid references users(id) on delete set null,created_at timestamp not null default now(),updated_at timestamp not null default now(),closed_at timestamp,cancelled_at timestamp,cancellation_reason text,check(due_at is null or opens_at is null or due_at>opens_at));create index idx_logbook_instances_event on logbook_instances(event_id);create index idx_logbook_instances_status on logbook_instances(status);
create table logbook_assignments(id uuid primary key default uuid_generate_v4(),logbook_instance_id uuid not null references logbook_instances(id) on delete cascade,user_id uuid not null references users(id) on delete restrict,assignment_role varchar(30) not null default 'PARTICIPANT',status logbook_assignment_status not null default 'PENDING',started_at timestamp,submitted_at timestamp,approved_at timestamp,approved_by uuid references users(id) on delete set null,changes_requested_at timestamp,changes_requested_by uuid references users(id) on delete set null,review_comment text,attempt_number integer not null default 0,created_at timestamp not null default now(),updated_at timestamp not null default now(),constraint uq_logbook_assignment_user unique(logbook_instance_id,user_id));
create table logbook_responses(id uuid primary key default uuid_generate_v4(),assignment_id uuid not null references logbook_assignments(id) on delete cascade,logbook_item_id uuid not null references logbook_items(id) on delete restrict,selected_option_id uuid references logbook_item_options(id) on delete restrict,boolean_value boolean,numeric_value numeric(14,4),text_value text,is_not_applicable boolean not null default false,result_status logbook_result_status not null,comment text,completed_by uuid references users(id) on delete set null,completed_at timestamp,created_at timestamp not null default now(),updated_at timestamp not null default now(),version integer not null default 1,constraint uq_logbook_response_item unique(assignment_id,logbook_item_id));
create table logbook_evidences(id uuid primary key default uuid_generate_v4(),instance_id uuid not null references logbook_instances(id) on delete restrict,assignment_id uuid not null references logbook_assignments(id) on delete restrict,item_id uuid not null references logbook_items(id) on delete restrict,response_id uuid not null references logbook_responses(id) on delete restrict,uploaded_by uuid references users(id) on delete set null,comment text,mime_type varchar(80) not null,file_size integer not null,original_filename varchar(255) not null,storage_key text not null,client_visible boolean not null default false,created_at timestamp not null default now(),deleted_at timestamp);create index idx_logbook_evidence_response on logbook_evidences(response_id);
create table logbook_review_history(id uuid primary key default uuid_generate_v4(),assignment_id uuid not null references logbook_assignments(id) on delete cascade,actor_id uuid references users(id) on delete set null,action varchar(40) not null,previous_status varchar(40),new_status varchar(40) not null,comment text,attempt_number integer not null,created_at timestamp not null default now());
""")
    for table in [
        "logbook_templates",
        "logbook_template_versions",
        "logbook_sections",
        "logbook_items",
        "logbook_item_options",
        "logbook_instances",
        "logbook_assignments",
        "logbook_responses",
        "logbook_evidences",
        "logbook_review_history",
    ]:
        op.execute(f"alter table {table} enable row level security")
        op.execute(
            f"create policy {table}_admin_all on {table} for all using (app_is_admin()) with check (app_is_admin())"
        )
    op.execute(
        """create policy logbook_instances_event_read on logbook_instances for select using (app_current_role()='CLIENT' and client_visibility and exists(select 1 from events e where e.id=event_id and e.client_id=app_current_client_id()) or exists(select 1 from event_staff es where es.event_id=event_id and es.user_id=app_current_user_id()));create policy logbook_assignments_participant on logbook_assignments for select using(user_id=app_current_user_id());create policy logbook_assignments_participant_update on logbook_assignments for update using(user_id=app_current_user_id()) with check(user_id=app_current_user_id());create policy logbook_responses_participant on logbook_responses for all using(exists(select 1 from logbook_assignments a where a.id=assignment_id and a.user_id=app_current_user_id())) with check(exists(select 1 from logbook_assignments a where a.id=assignment_id and a.user_id=app_current_user_id()));"""
    )


def downgrade():
    for t in [
        "logbook_review_history",
        "logbook_evidences",
        "logbook_responses",
        "logbook_assignments",
        "logbook_instances",
        "logbook_item_options",
        "logbook_items",
        "logbook_sections",
        "logbook_template_versions",
        "logbook_templates",
    ]:
        op.execute(f"drop table if exists {t} cascade")
    for n in reversed(list(ENUMS)):
        op.execute(f"drop type if exists {n}")
