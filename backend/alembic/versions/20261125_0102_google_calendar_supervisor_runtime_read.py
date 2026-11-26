"""Allow assigned supervisors to trigger Calendar sync without managing OAuth."""

from collections.abc import Sequence

from alembic import op


revision: str = "20261125_0102"
down_revision: str | None = "20261125_0101"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DROP POLICY IF EXISTS google_calendar_admin_service_access ON google_calendar_connections")
    op.execute(
        "CREATE POLICY google_calendar_runtime_read ON google_calendar_connections "
        "FOR SELECT USING (app_current_role() IN ('SUPER_ADMIN', 'ADMIN', 'SUPERVISOR'))"
    )
    op.execute(
        "CREATE POLICY google_calendar_super_admin_write ON google_calendar_connections "
        "FOR ALL USING (app_current_role() = 'SUPER_ADMIN') "
        "WITH CHECK (app_current_role() = 'SUPER_ADMIN')"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS google_calendar_super_admin_write ON google_calendar_connections")
    op.execute("DROP POLICY IF EXISTS google_calendar_runtime_read ON google_calendar_connections")
    op.execute(
        "CREATE POLICY google_calendar_admin_service_access ON google_calendar_connections "
        "FOR ALL USING (app_current_role() IN ('SUPER_ADMIN', 'ADMIN')) "
        "WITH CHECK (app_current_role() IN ('SUPER_ADMIN', 'ADMIN'))"
    )
