"""Integrate show staffing, tasks, incidents and evidences.

Revision ID: 20260806_0040
Revises: 20260804_0039
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260806_0040"
down_revision = "20260804_0039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint("uq_event_staff_event_id_id", "event_staff", ["event_id", "id"])
    op.create_unique_constraint("uq_tasks_event_id_id", "tasks", ["event_id", "id"])
    op.create_unique_constraint("uq_incidents_event_id_id", "incidents", ["event_id", "id"])

    op.add_column("tasks", sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("incidents", sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("incidents", sa.Column("source_task_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("evidences", sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("tasks", sa.Column("source_incident_id", postgresql.UUID(as_uuid=True), nullable=True))

    op.drop_constraint("evidences_task_id_fkey", "evidences", type_="foreignkey")
    op.drop_constraint("evidences_incident_id_fkey", "evidences", type_="foreignkey")
    op.create_foreign_key("fk_tasks_event_session", "tasks", "event_sessions", ["event_id", "session_id"], ["event_id", "id"], ondelete="RESTRICT")
    op.create_foreign_key("fk_incidents_event_session", "incidents", "event_sessions", ["event_id", "session_id"], ["event_id", "id"], ondelete="RESTRICT")
    op.create_foreign_key("fk_incidents_source_task", "incidents", "tasks", ["event_id", "source_task_id"], ["event_id", "id"], ondelete="RESTRICT")
    op.create_foreign_key("fk_tasks_source_incident", "tasks", "incidents", ["event_id", "source_incident_id"], ["event_id", "id"], ondelete="RESTRICT")
    op.create_foreign_key("fk_evidences_event_session", "evidences", "event_sessions", ["event_id", "session_id"], ["event_id", "id"], ondelete="RESTRICT")
    op.create_foreign_key("fk_evidences_event_task", "evidences", "tasks", ["event_id", "task_id"], ["event_id", "id"], ondelete="RESTRICT")
    op.create_foreign_key("fk_evidences_event_incident", "evidences", "incidents", ["event_id", "incident_id"], ["event_id", "id"], ondelete="RESTRICT")
    op.create_index("idx_tasks_event_session", "tasks", ["event_id", "session_id"])
    op.create_index("idx_incidents_event_session", "incidents", ["event_id", "session_id"])
    op.create_index("idx_incidents_source_task_id", "incidents", ["source_task_id"])
    op.create_index("uq_tasks_source_incident_id", "tasks", ["source_incident_id"], unique=True, postgresql_where=sa.text("source_incident_id is not null"))
    op.create_index("idx_evidences_event_session", "evidences", ["event_id", "session_id"])

    op.create_table(
        "event_session_staff",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_staff_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shift_start", sa.DateTime(), nullable=True),
        sa.Column("shift_end", sa.DateTime(), nullable=True),
        sa.Column("operational_role", sa.String(length=100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("shift_start is null or shift_end is null or shift_start < shift_end", name="ck_event_session_staff_shift"),
        sa.ForeignKeyConstraint(["event_id", "session_id"], ["event_sessions.event_id", "event_sessions.id"], name="fk_event_session_staff_session", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id", "event_staff_id"], ["event_staff.event_id", "event_staff.id"], name="fk_event_session_staff_event_staff", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_event_session_staff_created_by", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "event_staff_id", name="uq_event_session_staff_assignment"),
    )
    op.create_index("idx_event_session_staff_event", "event_session_staff", ["event_id"])
    op.create_index("idx_event_session_staff_session", "event_session_staff", ["session_id"])
    op.create_index("idx_event_session_staff_person", "event_session_staff", ["event_staff_id"])
    op.execute("alter table event_session_staff enable row level security")
    op.execute("create policy event_session_staff_select on event_session_staff for select using (app_is_admin() or (app_current_role()='SUPERVISOR' and app_can_view_event(event_id)) or exists (select 1 from event_staff es where es.id=event_staff_id and es.user_id=app_current_user_id()))")
    op.execute("create policy event_session_staff_insert on event_session_staff for insert with check (app_is_admin() or (app_current_role()='SUPERVISOR' and app_can_view_event(event_id)))")
    op.execute("create policy event_session_staff_update on event_session_staff for update using (app_is_admin() or (app_current_role()='SUPERVISOR' and app_can_view_event(event_id))) with check (app_is_admin() or (app_current_role()='SUPERVISOR' and app_can_view_event(event_id)))")
    op.execute("create policy event_session_staff_delete on event_session_staff for delete using (app_is_admin() or (app_current_role()='SUPERVISOR' and app_can_view_event(event_id)))")

    for table in ("tasks", "incidents", "evidences"):
        op.execute(f"drop policy if exists {table}_rls on {table}")
    op.execute("create policy tasks_select on tasks for select using (app_is_admin() or (app_current_role()='SUPERVISOR' and app_can_view_event(event_id)) or (app_current_role()='WORKER' and assigned_to=app_current_user_id()))")
    op.execute("create policy tasks_insert on tasks for insert with check (app_is_admin() or (app_current_role()='SUPERVISOR' and app_can_view_event(event_id)))")
    op.execute("create policy tasks_update on tasks for update using (app_is_admin() or (app_current_role()='SUPERVISOR' and app_can_view_event(event_id)) or (app_current_role()='WORKER' and assigned_to=app_current_user_id() and app_can_view_event(event_id))) with check (app_is_admin() or (app_current_role()='SUPERVISOR' and app_can_view_event(event_id)) or (app_current_role()='WORKER' and assigned_to=app_current_user_id() and app_can_view_event(event_id)))")
    op.execute("create policy tasks_delete on tasks for delete using (app_is_admin() or (app_current_role()='SUPERVISOR' and app_can_view_event(event_id)))")
    op.execute("create policy incidents_select on incidents for select using (app_is_admin() or (app_current_role()='SUPERVISOR' and app_can_view_event(event_id)) or (app_current_role()='WORKER' and (reported_by=app_current_user_id() or assigned_to=app_current_user_id())))")
    op.execute("create policy incidents_insert on incidents for insert with check (app_is_admin() or (app_current_role() in ('SUPERVISOR','WORKER') and app_can_view_event(event_id)))")
    op.execute("create policy incidents_update on incidents for update using (app_is_admin() or (app_current_role()='SUPERVISOR' and app_can_view_event(event_id))) with check (app_is_admin() or (app_current_role()='SUPERVISOR' and app_can_view_event(event_id)))")
    op.execute("create policy incidents_delete on incidents for delete using (app_is_admin() or (app_current_role()='SUPERVISOR' and app_can_view_event(event_id)))")
    op.execute("create policy evidences_select on evidences for select using (app_can_view_event(event_id) or uploaded_by=app_current_user_id())")
    op.execute("create policy evidences_insert on evidences for insert with check (app_is_admin() or (app_current_role() in ('SUPERVISOR','WORKER') and app_can_view_event(event_id)))")
    op.execute("create policy evidences_update on evidences for update using (app_is_admin() or (app_current_role()='SUPERVISOR' and app_can_view_event(event_id)) or (app_current_role()='WORKER' and uploaded_by=app_current_user_id() and app_can_view_event(event_id))) with check (app_is_admin() or (app_current_role()='SUPERVISOR' and app_can_view_event(event_id)) or (app_current_role()='WORKER' and uploaded_by=app_current_user_id() and app_can_view_event(event_id)))")
    op.execute("create policy evidences_delete on evidences for delete using (app_is_admin() or (app_current_role()='SUPERVISOR' and app_can_view_event(event_id)) or (app_current_role()='WORKER' and uploaded_by=app_current_user_id() and app_can_view_event(event_id)))")


def downgrade() -> None:
    for table in ("tasks", "incidents", "evidences"):
        for action in ("delete", "update", "insert", "select"):
            op.execute(f"drop policy if exists {table}_{action} on {table}")
    op.execute("create policy tasks_rls on tasks for all using (app_can_view_event(event_id) or assigned_to=app_current_user_id()) with check (app_can_view_event(event_id))")
    op.execute("create policy incidents_rls on incidents for all using (app_can_view_event(event_id) or reported_by=app_current_user_id() or assigned_to=app_current_user_id()) with check (app_can_view_event(event_id))")
    op.execute("create policy evidences_rls on evidences for all using (app_can_view_event(event_id) or uploaded_by=app_current_user_id()) with check (app_can_view_event(event_id) or uploaded_by=app_current_user_id())")
    for policy in ("event_session_staff_delete", "event_session_staff_update", "event_session_staff_insert", "event_session_staff_select"):
        op.execute(f"drop policy if exists {policy} on event_session_staff")
    op.drop_table("event_session_staff")
    op.drop_index("idx_evidences_event_session", table_name="evidences")
    op.drop_index("uq_tasks_source_incident_id", table_name="tasks")
    op.drop_index("idx_incidents_source_task_id", table_name="incidents")
    op.drop_index("idx_incidents_event_session", table_name="incidents")
    op.drop_index("idx_tasks_event_session", table_name="tasks")
    op.drop_constraint("fk_evidences_event_session", "evidences", type_="foreignkey")
    op.drop_constraint("fk_evidences_event_incident", "evidences", type_="foreignkey")
    op.drop_constraint("fk_evidences_event_task", "evidences", type_="foreignkey")
    op.create_foreign_key("evidences_task_id_fkey", "evidences", "tasks", ["task_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("evidences_incident_id_fkey", "evidences", "incidents", ["incident_id"], ["id"], ondelete="SET NULL")
    op.drop_constraint("fk_tasks_source_incident", "tasks", type_="foreignkey")
    op.drop_constraint("fk_incidents_source_task", "incidents", type_="foreignkey")
    op.drop_constraint("fk_incidents_event_session", "incidents", type_="foreignkey")
    op.drop_constraint("fk_tasks_event_session", "tasks", type_="foreignkey")
    op.drop_column("tasks", "source_incident_id")
    op.drop_column("evidences", "session_id")
    op.drop_column("incidents", "source_task_id")
    op.drop_column("incidents", "session_id")
    op.drop_column("tasks", "session_id")
    op.drop_constraint("uq_incidents_event_id_id", "incidents", type_="unique")
    op.drop_constraint("uq_tasks_event_id_id", "tasks", type_="unique")
    op.drop_constraint("uq_event_staff_event_id_id", "event_staff", type_="unique")
