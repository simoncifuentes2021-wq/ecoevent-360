"""Add event-specific PPE item templates for newly created documents."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20261014_0082"
down_revision: str | None = "20261006_0081"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_event_epp_templates",
        sa.Column(
            "event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("items", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "updated_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.execute("alter table document_event_epp_templates enable row level security")
    op.execute("""
        create policy document_event_epp_templates_read on document_event_epp_templates
        for select using (exists (
            select 1 from events e where e.id = event_id
              and (app_documents_can_access_client(e.client_id)
                or app_documents_can_access_event(e.id, e.client_id))
        ))
    """)
    op.execute("""
        create policy document_event_epp_templates_write on document_event_epp_templates
        for all using (exists (
            select 1 from events e where e.id = event_id
              and app_documents_can_access_client(e.client_id)
        )) with check (exists (
            select 1 from events e where e.id = event_id
              and app_documents_can_access_client(e.client_id)
        ))
    """)


def downgrade() -> None:
    op.execute("drop policy if exists document_event_epp_templates_write on document_event_epp_templates")
    op.execute("drop policy if exists document_event_epp_templates_read on document_event_epp_templates")
    op.drop_table("document_event_epp_templates")
