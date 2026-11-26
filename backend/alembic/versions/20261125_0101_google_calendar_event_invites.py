"""Persist Google Calendar event and staff invitation delivery state."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20261125_0101"
down_revision: str | None = "20261124_0100"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DROP POLICY IF EXISTS google_calendar_super_admin_only ON google_calendar_connections")
    op.execute(
        "CREATE POLICY google_calendar_admin_service_access ON google_calendar_connections "
        "FOR ALL USING (app_current_role() IN ('SUPER_ADMIN', 'ADMIN')) "
        "WITH CHECK (app_current_role() IN ('SUPER_ADMIN', 'ADMIN'))"
    )
    op.add_column("events", sa.Column("google_calendar_event_id", sa.String(length=128), nullable=True))
    op.add_column(
        "event_staff",
        sa.Column("calendar_invitation_status", sa.String(length=16), server_default="PENDING", nullable=False),
    )
    op.add_column("event_staff", sa.Column("calendar_invitation_error", sa.Text(), nullable=True))
    op.add_column("event_staff", sa.Column("calendar_invitation_sent_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("event_staff", "calendar_invitation_sent_at")
    op.drop_column("event_staff", "calendar_invitation_error")
    op.drop_column("event_staff", "calendar_invitation_status")
    op.drop_column("events", "google_calendar_event_id")
    op.execute("DROP POLICY IF EXISTS google_calendar_admin_service_access ON google_calendar_connections")
    op.execute(
        "CREATE POLICY google_calendar_super_admin_only ON google_calendar_connections "
        "FOR ALL USING (app_current_role() = 'SUPER_ADMIN') "
        "WITH CHECK (app_current_role() = 'SUPER_ADMIN')"
    )
