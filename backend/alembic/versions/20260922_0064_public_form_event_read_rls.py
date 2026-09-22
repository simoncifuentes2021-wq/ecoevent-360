"""Allow public forms to read their event metadata through RLS.

Revision ID: 20260922_0064
Revises: 20260910_0063
"""

from collections.abc import Sequence

from alembic import op


revision: str = "20260922_0064"
down_revision: str | None = "20260910_0063"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


PUBLIC_FORM_ID = "nullif(current_setting('app.public_form_id', true), '')::uuid"


def upgrade() -> None:
    op.execute(
        f"""
        create policy events_public_form_read on events for select
        using (exists (
            select 1 from event_forms f
            where f.id = {PUBLIC_FORM_ID}
              and f.event_id = events.id
              and f.status = 'ACTIVE'
        ))
        """
    )
    op.execute(
        f"""
        create policy event_sessions_public_form_read on event_sessions for select
        using (exists (
            select 1 from event_forms f
            where f.id = {PUBLIC_FORM_ID}
              and f.event_id = event_sessions.event_id
              and f.session_id = event_sessions.id
              and f.status = 'ACTIVE'
        ))
        """
    )


def downgrade() -> None:
    op.execute("drop policy if exists event_sessions_public_form_read on event_sessions")
    op.execute("drop policy if exists events_public_form_read on events")
