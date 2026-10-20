"""Store reusable Greenway employer details for contracts."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20261006_0081"
down_revision: str | None = "20261006_0080"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_contract_defaults",
        sa.Column("settings_key", sa.String(length=40), primary_key=True),
        sa.Column(
            "defaults",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "updated_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")
        ),
    )
    op.execute("alter table document_contract_defaults enable row level security")
    op.execute("""
        create policy document_contract_defaults_read on document_contract_defaults
        for select using (app_current_role() in ('SUPER_ADMIN', 'ADMIN', 'SUPERVISOR'))
    """)
    op.execute("""
        create policy document_contract_defaults_write on document_contract_defaults
        for all using (app_is_admin()) with check (app_is_admin())
    """)


def downgrade() -> None:
    op.execute("drop policy if exists document_contract_defaults_write on document_contract_defaults")
    op.execute("drop policy if exists document_contract_defaults_read on document_contract_defaults")
    op.drop_table("document_contract_defaults")
