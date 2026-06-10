"""allow auth audit logs before an authenticated rls context

Revision ID: 20260610_0006
Revises: 20260610_0005
Create Date: 2026-06-10
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260610_0006"
down_revision: str | None = "20260610_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("drop policy if exists audit_logs_rls on audit_logs")
    op.execute(
        """
        create policy audit_logs_rls on audit_logs
            for all
            using (
                app_is_admin()
                or user_id = app_current_user_id()
                or (client_id is not null and app_can_access_client(client_id))
                or (event_id is not null and app_can_view_event(event_id))
            )
            with check (
                app_is_authenticated()
                or module = 'auth'
            );
        """
    )


def downgrade() -> None:
    op.execute("drop policy if exists audit_logs_rls on audit_logs")
    op.execute(
        """
        create policy audit_logs_rls on audit_logs
            for all
            using (
                app_is_admin()
                or user_id = app_current_user_id()
                or (client_id is not null and app_can_access_client(client_id))
                or (event_id is not null and app_can_view_event(event_id))
            )
            with check (app_is_authenticated());
        """
    )
