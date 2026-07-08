"""fix events rls policy for insert returning

Revision ID: 20260708_0027
Revises: 20260703_0026
Create Date: 2026-07-08
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260708_0027"
down_revision: str | None = "20260703_0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        drop policy if exists events_rls on events;

        create policy events_rls on events
            for all
            using (
                app_is_admin()
                or (
                    app_current_role() = 'CLIENT'
                    and app_current_client_id() = client_id
                )
                or (
                    app_current_role() in ('SUPERVISOR', 'WORKER', 'LOGISTICS_OPERATOR')
                    and status <> 'QUOTE'
                    and hidden_from_operations = false
                    and (
                        exists (
                            select 1
                            from event_staff es
                            where es.event_id = events.id
                              and es.user_id = app_current_user_id()
                        )
                        or exists (
                            select 1
                            from tasks t
                            where t.event_id = events.id
                              and t.assigned_to = app_current_user_id()
                        )
                    )
                )
            )
            with check (
                app_is_admin()
                or app_can_access_client(client_id)
            );
        """
    )


def downgrade() -> None:
    op.execute(
        """
        drop policy if exists events_rls on events;

        create policy events_rls on events
            for all
            using (app_can_view_event(id))
            with check (app_is_admin() or app_can_access_client(client_id));
        """
    )
