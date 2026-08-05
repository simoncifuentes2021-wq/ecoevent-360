"""Turn event sessions into an operational entity.

Revision ID: 20260804_0039
Revises: 20260802_0038
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260804_0039"
down_revision = "20260802_0038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("event_sessions", sa.Column("responsible_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("event_sessions", sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False))
    op.add_column("event_sessions", sa.Column("internal_notes", sa.Text(), nullable=True))
    op.add_column("event_sessions", sa.Column("archived_at", sa.DateTime(), nullable=True))
    op.create_foreign_key("fk_event_sessions_responsible_id_users", "event_sessions", "users", ["responsible_id"], ["id"], ondelete="SET NULL")
    op.create_unique_constraint("uq_event_sessions_event_id_id", "event_sessions", ["event_id", "id"])
    op.create_check_constraint("ck_event_sessions_expected_attendees", "event_sessions", "expected_attendees >= 0")
    op.create_check_constraint("ck_event_sessions_real_attendees", "event_sessions", "real_attendees is null or real_attendees >= 0")
    op.create_check_constraint("ck_event_sessions_sort_order", "event_sessions", "sort_order >= 0")
    op.create_check_constraint("ck_event_sessions_status", "event_sessions", "status in ('PLANNED','READY','IN_PROGRESS','COMPLETED','CANCELLED')")
    op.create_index("idx_event_sessions_responsible_id", "event_sessions", ["responsible_id"])
    op.create_index("idx_event_sessions_event_sort_order", "event_sessions", ["event_id", "sort_order"])

    op.execute("drop policy if exists event_sessions_rls on event_sessions")
    op.execute("create policy event_sessions_select on event_sessions for select using (app_can_view_event(event_id))")
    op.execute("""
        create policy event_sessions_insert on event_sessions for insert
        with check (app_is_admin() or (app_current_role() = 'SUPERVISOR' and app_can_view_event(event_id)))
    """)
    op.execute("""
        create policy event_sessions_update on event_sessions for update
        using (app_is_admin() or (app_current_role() = 'SUPERVISOR' and app_can_view_event(event_id)))
        with check (app_is_admin() or (app_current_role() = 'SUPERVISOR' and app_can_view_event(event_id)))
    """)
    op.execute("""
        create policy event_sessions_delete on event_sessions for delete
        using (app_is_admin() or (app_current_role() = 'SUPERVISOR' and app_can_view_event(event_id)))
    """)


def downgrade() -> None:
    for policy in ("event_sessions_delete", "event_sessions_update", "event_sessions_insert", "event_sessions_select"):
        op.execute(f"drop policy if exists {policy} on event_sessions")
    op.execute("create policy event_sessions_rls on event_sessions for all using (app_can_view_event(event_id)) with check (app_can_view_event(event_id))")
    op.drop_index("idx_event_sessions_event_sort_order", table_name="event_sessions")
    op.drop_index("idx_event_sessions_responsible_id", table_name="event_sessions")
    op.drop_constraint("ck_event_sessions_status", "event_sessions", type_="check")
    op.drop_constraint("ck_event_sessions_sort_order", "event_sessions", type_="check")
    op.drop_constraint("ck_event_sessions_real_attendees", "event_sessions", type_="check")
    op.drop_constraint("ck_event_sessions_expected_attendees", "event_sessions", type_="check")
    op.drop_constraint("uq_event_sessions_event_id_id", "event_sessions", type_="unique")
    op.drop_constraint("fk_event_sessions_responsible_id_users", "event_sessions", type_="foreignkey")
    op.drop_column("event_sessions", "archived_at")
    op.drop_column("event_sessions", "internal_notes")
    op.drop_column("event_sessions", "sort_order")
    op.drop_column("event_sessions", "responsible_id")
