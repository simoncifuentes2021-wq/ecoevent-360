"""Add daily Excel logbook imports and individual contributions.

Revision ID: 20260814_0046
Revises: 20260814_0045
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260814_0046"
down_revision = "20260814_0045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint("uq_logbook_assignment_instance", "logbook_assignments", ["id", "logbook_instance_id"])
    op.create_table("logbook_import_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("events.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False), sa.Column("file_sha256", sa.String(64), nullable=False),
        sa.Column("sheet_name", sa.String(180), nullable=False), sa.Column("activities_count", sa.Integer, nullable=False),
        sa.Column("dates_count", sa.Integer, nullable=False), sa.Column("scheduled_items_count", sa.Integer, nullable=False),
        sa.Column("instances_created", sa.Integer, nullable=False), sa.Column("status", sa.String(30), nullable=False, server_default="COMPLETED"),
        sa.Column("configuration", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("imported_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("event_id", "file_sha256", name="uq_logbook_import_event_sha"),
        sa.UniqueConstraint("id", "event_id", name="uq_logbook_import_batch_event"))
    op.create_index("idx_logbook_import_event_created", "logbook_import_batches", ["event_id", "created_at"])
    op.add_column("logbook_instances", sa.Column("import_batch_id", postgresql.UUID(as_uuid=True)))
    op.create_foreign_key("fk_logbook_instance_import_batch", "logbook_instances", "logbook_import_batches", ["import_batch_id"], ["id"], ondelete="RESTRICT")
    op.create_table("logbook_instance_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("instance_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("logbook_instances.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(180), nullable=False), sa.Column("source_row", sa.Integer, nullable=False),
        sa.Column("position", sa.Integer, nullable=False), sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("source_row > 0", name="ck_logbook_instance_item_source_row"),
        sa.UniqueConstraint("instance_id", "position", name="uq_logbook_instance_item_position"),
        sa.UniqueConstraint("id", "instance_id", name="uq_logbook_instance_item_instance"))
    op.create_index("idx_logbook_instance_items_instance", "logbook_instance_items", ["instance_id"])
    op.create_table("logbook_item_contributions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("instance_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assignment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("instance_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("logbook_instances.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("description", sa.Text, nullable=False), sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")), sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True)), sa.CheckConstraint("version > 0", name="ck_logbook_contribution_version"),
        sa.UniqueConstraint("instance_item_id", "assignment_id", name="uq_logbook_contribution_author"),
        sa.UniqueConstraint("id", "instance_id", "instance_item_id", "assignment_id", name="uq_logbook_contribution_scope"),
        sa.ForeignKeyConstraint(["instance_item_id", "instance_id"], ["logbook_instance_items.id", "logbook_instance_items.instance_id"], name="fk_logbook_contribution_item_instance", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assignment_id", "instance_id"], ["logbook_assignments.id", "logbook_assignments.logbook_instance_id"], name="fk_logbook_contribution_assignment_instance", ondelete="CASCADE"))
    op.create_index("idx_logbook_contribution_item", "logbook_item_contributions", ["instance_item_id"])
    op.create_table("logbook_contribution_evidences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("contribution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("events.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("instance_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("logbook_instances.id", ondelete="CASCADE"), nullable=False),
        sa.Column("instance_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("logbook_instance_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assignment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("logbook_assignments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("mime_type", sa.String(80), nullable=False), sa.Column("file_size", sa.Integer, nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False), sa.Column("storage_key", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")), sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["contribution_id", "instance_id", "instance_item_id", "assignment_id"], ["logbook_item_contributions.id", "logbook_item_contributions.instance_id", "logbook_item_contributions.instance_item_id", "logbook_item_contributions.assignment_id"], name="fk_logbook_contribution_evidence_scope", ondelete="CASCADE"))
    op.create_index("idx_logbook_contribution_evidence", "logbook_contribution_evidences", ["contribution_id"])
    for table in ("logbook_import_batches", "logbook_instance_items", "logbook_item_contributions", "logbook_contribution_evidences"):
        op.execute(f"alter table {table} enable row level security")
        op.execute(f"alter table {table} force row level security")
    manage = "app_is_admin() or (app_current_role()='SUPERVISOR' and app_can_view_event(event_id))"
    op.execute(f"create policy logbook_import_batches_manage on logbook_import_batches for all using ({manage}) with check ({manage})")
    item_view = "exists(select 1 from logbook_instances li where li.id=instance_id and (app_is_admin() or (app_current_role()='SUPERVISOR' and app_can_view_event(li.event_id)) or exists(select 1 from logbook_assignments a where a.logbook_instance_id=li.id and a.user_id=app_current_user_id())))"
    op.execute(f"create policy logbook_instance_items_read on logbook_instance_items for select using ({item_view})")
    op.execute("create policy logbook_instance_items_manage on logbook_instance_items for all using (app_is_admin() or exists(select 1 from logbook_instances li where li.id=instance_id and app_current_role()='SUPERVISOR' and app_can_view_event(li.event_id))) with check (app_is_admin() or exists(select 1 from logbook_instances li where li.id=instance_id and app_current_role()='SUPERVISOR' and app_can_view_event(li.event_id)))")
    contribution_scope = "exists(select 1 from logbook_instances li where li.id=instance_id and (app_is_admin() or (app_current_role()='SUPERVISOR' and app_can_view_event(li.event_id)) or exists(select 1 from logbook_assignments viewer where viewer.logbook_instance_id=li.id and viewer.user_id=app_current_user_id())))"
    op.execute(f"create policy logbook_contributions_read on logbook_item_contributions for select using ({contribution_scope})")
    op.execute("create policy logbook_contributions_own_write on logbook_item_contributions for all using (author_id=app_current_user_id() and exists(select 1 from logbook_assignments a where a.id=assignment_id and a.user_id=app_current_user_id())) with check (author_id=app_current_user_id() and exists(select 1 from logbook_assignments a join logbook_instance_items ii on ii.instance_id=a.logbook_instance_id where a.id=assignment_id and ii.id=instance_item_id and a.user_id=app_current_user_id()))")
    evidence_scope = "exists(select 1 from logbook_item_contributions c join logbook_assignments a on a.id=c.assignment_id join logbook_instance_items ii on ii.id=c.instance_item_id join logbook_instances li on li.id=ii.instance_id where c.id=contribution_id and (app_is_admin() or (app_current_role()='SUPERVISOR' and app_can_view_event(li.event_id)) or a.user_id=app_current_user_id()))"
    op.execute(f"create policy logbook_contribution_evidence_read on logbook_contribution_evidences for select using ({evidence_scope})")
    op.execute("create policy logbook_contribution_evidence_own_write on logbook_contribution_evidences for all using (uploaded_by=app_current_user_id()) with check (uploaded_by=app_current_user_id() and exists(select 1 from logbook_item_contributions c join logbook_assignments a on a.id=c.assignment_id where c.id=contribution_id and c.author_id=app_current_user_id() and a.user_id=app_current_user_id()))")


def downgrade() -> None:
    op.drop_table("logbook_contribution_evidences")
    op.drop_table("logbook_item_contributions")
    op.drop_table("logbook_instance_items")
    op.drop_constraint("fk_logbook_instance_import_batch", "logbook_instances", type_="foreignkey")
    op.drop_column("logbook_instances", "import_batch_id")
    op.drop_table("logbook_import_batches")
    op.drop_constraint("uq_logbook_assignment_instance", "logbook_assignments", type_="unique")
