"""Add recurring logbook series and independent occurrences.

Revision ID: 20260802_0038
Revises: 20260727_0037
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260802_0038"
down_revision = "20260727_0037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for name, values in (
        ("logbook_recurrence_frequency", ("DAILY", "WEEKLY", "MONTHLY")),
        ("logbook_recurrence_end_mode", ("END_DATE", "COUNT")),
        ("logbook_recurrence_status", ("ACTIVE", "PAUSED", "FINISHED", "CANCELLED")),
        ("logbook_recurrence_exception_type", ("SKIPPED", "REPROGRAMMED", "NO_VALID_PARTICIPANTS")),
    ):
        postgresql.ENUM(*values, name=name).create(op.get_bind(), checkfirst=True)

    op.create_table(
        "logbook_recurrence_series",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("events.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("logbook_templates.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("template_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("logbook_template_versions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("operational_stage", postgresql.ENUM(name="logbook_operational_stage", create_type=False), nullable=False),
        sa.Column("zone_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("event_zones.id", ondelete="SET NULL")),
        sa.Column("assignment_mode", postgresql.ENUM(name="logbook_assignment_mode", create_type=False), nullable=False),
        sa.Column("supervisor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("client_visibility", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("frequency", postgresql.ENUM(name="logbook_recurrence_frequency", create_type=False), nullable=False),
        sa.Column("interval", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("weekdays", postgresql.JSONB()),
        sa.Column("day_of_month", sa.Integer()),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_mode", postgresql.ENUM(name="logbook_recurrence_end_mode", create_type=False), nullable=False),
        sa.Column("end_date", sa.Date()),
        sa.Column("max_occurrences", sa.Integer()),
        sa.Column("opens_at_local", sa.Time(), nullable=False),
        sa.Column("due_at_local", sa.Time(), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="America/Santiago"),
        sa.Column("status", postgresql.ENUM(name="logbook_recurrence_status", create_type=False), nullable=False, server_default="ACTIVE"),
        sa.Column("next_occurrence_date", sa.Date()),
        sa.Column("generated_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("interval > 0", name="ck_logbook_recurrence_interval"),
        sa.CheckConstraint("max_occurrences is null or (max_occurrences > 0 and max_occurrences <= 500)", name="ck_logbook_recurrence_max_occurrences"),
        sa.UniqueConstraint("id", "event_id", name="uq_logbook_recurrence_series_event"),
    )
    op.create_index("idx_logbook_recurrence_event_status", "logbook_recurrence_series", ["event_id", "status"])
    op.create_index("idx_logbook_recurrence_next", "logbook_recurrence_series", ["status", "next_occurrence_date"])
    op.create_table(
        "logbook_recurrence_participants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("series_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("series_id", "user_id", name="uq_logbook_recurrence_participant"),
        sa.ForeignKeyConstraint(
            ["series_id", "event_id"], ["logbook_recurrence_series.id", "logbook_recurrence_series.event_id"],
            name="fk_logbook_recurrence_participant_series_event", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["event_id", "user_id"], ["event_staff.event_id", "event_staff.user_id"],
            name="fk_logbook_recurrence_participant_event_staff", ondelete="CASCADE",
        ),
    )
    op.create_table(
        "logbook_recurrence_exceptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("series_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("logbook_recurrence_series.id", ondelete="CASCADE"), nullable=False),
        sa.Column("original_date", sa.Date(), nullable=False),
        sa.Column("exception_type", postgresql.ENUM(name="logbook_recurrence_exception_type", create_type=False), nullable=False),
        sa.Column("replacement_date", sa.Date()),
        sa.Column("reason", sa.Text()),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("series_id", "original_date", name="uq_logbook_recurrence_exception_date"),
    )
    op.add_column("logbook_instances", sa.Column("recurrence_series_id", postgresql.UUID(as_uuid=True)))
    op.add_column("logbook_instances", sa.Column("occurrence_date", sa.Date()))
    op.add_column("logbook_instances", sa.Column("occurrence_modified", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("logbook_instances", sa.Column("original_occurrence_date", sa.Date()))
    op.create_foreign_key(
        "fk_logbook_instance_recurrence_event", "logbook_instances", "logbook_recurrence_series",
        ["recurrence_series_id", "event_id"], ["id", "event_id"], ondelete="RESTRICT",
    )
    op.create_unique_constraint("uq_logbook_instance_recurrence_date", "logbook_instances", ["recurrence_series_id", "occurrence_date"])
    op.create_index("idx_logbook_instances_recurrence", "logbook_instances", ["recurrence_series_id", "occurrence_date"])

    for table in ("logbook_recurrence_series", "logbook_recurrence_participants", "logbook_recurrence_exceptions"):
        op.execute(f"alter table {table} enable row level security")
        op.execute(f"create policy {table}_admin_all on {table} for all using (app_is_admin()) with check (app_is_admin())")
    supervisor_scope = "app_current_role()='SUPERVISOR' and exists(select 1 from event_staff es where es.event_id=logbook_recurrence_series.event_id and es.user_id=app_current_user_id())"
    op.execute(f"create policy logbook_recurrence_series_supervisor on logbook_recurrence_series for all using ({supervisor_scope}) with check ({supervisor_scope})")
    participant_scope = "exists(select 1 from logbook_recurrence_series s join event_staff es on es.event_id=s.event_id where s.id=logbook_recurrence_participants.series_id and app_current_role()='SUPERVISOR' and es.user_id=app_current_user_id())"
    exception_scope = "exists(select 1 from logbook_recurrence_series s join event_staff es on es.event_id=s.event_id where s.id=logbook_recurrence_exceptions.series_id and app_current_role()='SUPERVISOR' and es.user_id=app_current_user_id())"
    op.execute(f"create policy logbook_recurrence_participants_supervisor on logbook_recurrence_participants for all using ({participant_scope}) with check ({participant_scope})")
    op.execute(f"create policy logbook_recurrence_exceptions_supervisor on logbook_recurrence_exceptions for all using ({exception_scope}) with check ({exception_scope})")
    op.execute("drop policy if exists logbook_instances_event_read on logbook_instances")
    op.execute("""
      create policy logbook_instances_event_read on logbook_instances for select using (
        app_current_role()='CLIENT' and client_visibility and exists(
          select 1 from events e
          where e.id=logbook_instances.event_id and e.client_id=app_current_client_id()
        ) or exists(
          select 1 from event_staff es
          where es.event_id=logbook_instances.event_id and es.user_id=app_current_user_id()
        )
      )
    """)


def downgrade() -> None:
    op.execute("drop policy if exists logbook_instances_event_read on logbook_instances")
    op.execute("""
      create policy logbook_instances_event_read on logbook_instances for select using (
        app_current_role()='CLIENT' and client_visibility and exists(
          select 1 from events e where e.id=event_id and e.client_id=app_current_client_id()
        ) or exists(
          select 1 from event_staff es
          where es.event_id=event_id and es.user_id=app_current_user_id()
        )
      )
    """)
    op.drop_index("idx_logbook_instances_recurrence", table_name="logbook_instances")
    op.drop_constraint("uq_logbook_instance_recurrence_date", "logbook_instances", type_="unique")
    op.drop_constraint("fk_logbook_instance_recurrence_event", "logbook_instances", type_="foreignkey")
    for column in ("original_occurrence_date", "occurrence_modified", "occurrence_date", "recurrence_series_id"):
        op.drop_column("logbook_instances", column)
    op.drop_table("logbook_recurrence_exceptions")
    op.drop_table("logbook_recurrence_participants")
    op.drop_index("idx_logbook_recurrence_next", table_name="logbook_recurrence_series")
    op.drop_index("idx_logbook_recurrence_event_status", table_name="logbook_recurrence_series")
    op.drop_table("logbook_recurrence_series")
    for name in ("logbook_recurrence_exception_type", "logbook_recurrence_status", "logbook_recurrence_end_mode", "logbook_recurrence_frequency"):
        postgresql.ENUM(name=name).drop(op.get_bind(), checkfirst=True)
