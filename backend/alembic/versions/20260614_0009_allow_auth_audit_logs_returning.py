"""allow auth audit logs to be returned after insert

Revision ID: 20260614_0009
Revises: 20260612_0008
Create Date: 2026-06-14
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260614_0009"
down_revision: str | None = "20260612_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("drop policy if exists audit_logs_rls on audit_logs")
    op.execute(
        """
        create policy audit_logs_rls on audit_logs
            for all
            using (
                module = 'auth'
                or app_is_admin()
                or user_id = app_current_user_id()
                or (client_id is not null and app_can_access_client(client_id))
                or (event_id is not null and app_can_view_event(event_id))
            )
            with check (
                module = 'auth'
                or app_is_authenticated()
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
            with check (
                app_is_authenticated()
                or module = 'auth'
            );
        """
    )
