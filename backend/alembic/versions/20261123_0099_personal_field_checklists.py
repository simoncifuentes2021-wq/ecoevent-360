"""Add personal field checklists with due-time email reminders."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20261123_0099"
down_revision: str | None = "20261120_0098"
branch_labels: str | Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "field_checklist_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("due_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="PENDING", nullable=False),
        sa.Column("status_note", sa.Text(), nullable=True),
        sa.Column("reminder_sent_at", sa.DateTime(), nullable=True),
        sa.Column("reminder_attempted_at", sa.DateTime(), nullable=True),
        sa.Column("reminder_attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("status in ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'BLOCKED')", name="ck_field_checklist_status"),
    )
    op.create_index("idx_field_checklist_event_user_due", "field_checklist_items", ["event_id", "user_id", "due_at"])
    op.create_index("idx_field_checklist_reminders", "field_checklist_items", ["status", "due_at", "reminder_sent_at"])
    op.create_table(
        "field_checklist_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["item_id"], ["field_checklist_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_field_checklist_history_item_created", "field_checklist_history", ["item_id", "created_at"])
    op.execute("ALTER TABLE field_checklist_items ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE field_checklist_history ENABLE ROW LEVEL SECURITY")
    op.execute("CREATE POLICY field_checklist_items_event_access ON field_checklist_items FOR ALL USING (app_can_view_event(event_id) AND (app_current_role() = 'SUPER_ADMIN' OR user_id = app_current_user_id())) WITH CHECK (app_can_view_event(event_id) AND (app_current_role() = 'SUPER_ADMIN' OR user_id = app_current_user_id()))")
    op.execute("CREATE POLICY field_checklist_history_event_access ON field_checklist_history FOR ALL USING (app_can_view_event(event_id) AND (app_current_role() = 'SUPER_ADMIN' OR EXISTS (SELECT 1 FROM field_checklist_items i WHERE i.id = item_id AND i.user_id = app_current_user_id()))) WITH CHECK (app_can_view_event(event_id) AND (app_current_role() = 'SUPER_ADMIN' OR EXISTS (SELECT 1 FROM field_checklist_items i WHERE i.id = item_id AND i.user_id = app_current_user_id())))")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS field_checklist_history_event_access ON field_checklist_history")
    op.execute("DROP POLICY IF EXISTS field_checklist_items_event_access ON field_checklist_items")
    op.drop_index("idx_field_checklist_history_item_created", table_name="field_checklist_history")
    op.drop_table("field_checklist_history")
    op.drop_index("idx_field_checklist_reminders", table_name="field_checklist_items")
    op.drop_index("idx_field_checklist_event_user_due", table_name="field_checklist_items")
    op.drop_table("field_checklist_items")
