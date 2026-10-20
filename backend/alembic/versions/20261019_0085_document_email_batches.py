"""Add resumable, persistent document email batches."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20261019_0085"
down_revision: str | None = "20261019_0084"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_ACCESS = """(
    (app_current_role() in ('SUPER_ADMIN', 'ADMIN')
        and app_documents_can_access_client(client_id))
    or (app_current_role() = 'SUPERVISOR' and app_can_view_event(event_id))
)"""


def upgrade() -> None:
    op.create_table(
        "document_email_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "client_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False,
        ),
        sa.Column(
            "event_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "created_by", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False,
        ),
        sa.Column("status", sa.String(32), nullable=False, server_default="QUEUED"),
        sa.Column("total_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint("total_count >= 0 and total_count <= 500", name="ck_document_email_batches_total"),
        sa.CheckConstraint(
            "status in ('QUEUED', 'PROCESSING', 'COMPLETED', 'COMPLETED_WITH_ERRORS')",
            name="ck_document_email_batches_status",
        ),
    )
    op.create_index("idx_document_email_batches_event", "document_email_batches", ["event_id", "created_at"])
    op.create_index("idx_document_email_batches_actor", "document_email_batches", ["created_by", "created_at"])

    op.create_table(
        "document_email_batch_items",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "batch_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("document_email_batches.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "client_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False,
        ),
        sa.Column(
            "event_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "contract_document_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("managed_documents.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "epp_document_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("managed_documents.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "created_by", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False,
        ),
        sa.Column("status", sa.String(24), nullable=False, server_default="QUEUED"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("locked_at", sa.DateTime()),
        sa.Column("error", sa.Text()),
        sa.Column("result", postgresql.JSONB()),
        sa.Column("delivery_payload", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("batch_id", "contract_document_id", name="uq_document_email_batch_contract"),
        sa.CheckConstraint(
            "status in ('QUEUED', 'PROCESSING', 'SENDING', 'RETRYING', 'SENT', 'PREPARED', 'FAILED')",
            name="ck_document_email_batch_items_status",
        ),
        sa.CheckConstraint("attempt_count >= 0 and attempt_count <= 5", name="ck_document_email_batch_items_attempts"),
    )
    op.create_index(
        "idx_document_email_batch_items_queue", "document_email_batch_items",
        ["status", "next_attempt_at", "created_at"],
    )
    op.create_index(
        "idx_document_email_batch_items_event", "document_email_batch_items",
        ["event_id", "created_at"],
    )

    for table in ("document_email_batches", "document_email_batch_items"):
        op.execute(f"alter table {table} enable row level security")
        op.execute(f"create policy {table}_event_access on {table} for all using {_ACCESS} with check {_ACCESS}")


def downgrade() -> None:
    for table in ("document_email_batch_items", "document_email_batches"):
        op.execute(f"drop policy if exists {table}_event_access on {table}")
        op.execute(f"alter table {table} disable row level security")
    op.drop_table("document_email_batch_items")
    op.drop_table("document_email_batches")
