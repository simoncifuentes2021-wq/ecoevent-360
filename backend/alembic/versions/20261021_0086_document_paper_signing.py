"""Persist paper-signing workflow and printable batch artifacts."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20261021_0086"
down_revision: str | None = "20261019_0085"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_ACCESS = """(
    (app_current_role() in ('SUPER_ADMIN', 'ADMIN')
        and app_documents_can_access_client(client_id))
    or (app_current_role() = 'SUPERVISOR' and app_can_view_event(event_id))
)"""


def upgrade() -> None:
    op.add_column("managed_documents", sa.Column("signature_method", sa.String(16)))
    op.add_column("managed_documents", sa.Column("paper_status", sa.String(24)))
    op.add_column("managed_documents", sa.Column("paper_printed_at", sa.DateTime()))
    op.add_column(
        "managed_documents",
        sa.Column("paper_printed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
    )
    op.add_column("managed_documents", sa.Column("paper_signed_received_at", sa.DateTime()))
    op.add_column(
        "managed_documents",
        sa.Column("paper_signed_received_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
    )
    op.add_column("managed_documents", sa.Column("paper_evidence_storage_key", sa.String(500)))
    op.add_column("managed_documents", sa.Column("paper_evidence_sha256", sa.String(64)))
    op.add_column("managed_documents", sa.Column("paper_evidence_content_type", sa.String(100)))
    op.add_column("managed_documents", sa.Column("paper_evidence_file_name", sa.String(180)))
    op.add_column("managed_documents", sa.Column("paper_evidence_uploaded_at", sa.DateTime()))
    op.add_column(
        "managed_documents",
        sa.Column("paper_evidence_uploaded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
    )
    op.create_check_constraint(
        "ck_managed_documents_signature_method",
        "managed_documents",
        "signature_method is null or signature_method in ('PAPER', 'ELECTRONIC')",
    )
    op.create_check_constraint(
        "ck_managed_documents_paper_status",
        "managed_documents",
        "paper_status is null or paper_status in ('PREPARED', 'PRINTED', 'SIGNED_RECEIVED', 'ARCHIVED')",
    )
    op.execute("""
        update managed_documents
        set signature_method = 'ELECTRONIC'
        where status in ('SENT', 'VIEWED', 'PARTIALLY_SIGNED', 'COMPLETED', 'EXPIRED')
    """)

    op.create_table(
        "document_paper_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("kinds", postgresql.JSONB(), nullable=False),
        sa.Column("people_count", sa.Integer(), nullable=False),
        sa.Column("document_count", sa.Integer(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("printed_at", sa.DateTime()),
        sa.Column("printed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint("people_count > 0 and people_count <= 200", name="ck_document_paper_batches_people"),
        sa.CheckConstraint("document_count > 0 and page_count > 0", name="ck_document_paper_batches_counts"),
    )
    op.create_index("idx_document_paper_batches_event", "document_paper_batches", ["event_id", "created_at"])
    op.create_table(
        "document_paper_batch_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("document_paper_batches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("managed_documents.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("person_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("document_people.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("document_version", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("batch_id", "document_id", name="uq_document_paper_batch_document"),
        sa.CheckConstraint("kind in ('CONTRACT', 'EPP')", name="ck_document_paper_batch_items_kind"),
    )
    op.create_index("idx_document_paper_batch_items_document", "document_paper_batch_items", ["document_id", "created_at"])

    for table in ("document_paper_batches", "document_paper_batch_items"):
        op.execute(f"alter table {table} enable row level security")
        op.execute(f"create policy {table}_event_access on {table} for all using {_ACCESS} with check {_ACCESS}")


def downgrade() -> None:
    for table in ("document_paper_batch_items", "document_paper_batches"):
        op.execute(f"drop policy if exists {table}_event_access on {table}")
        op.execute(f"alter table {table} disable row level security")
    op.drop_table("document_paper_batch_items")
    op.drop_table("document_paper_batches")
    op.drop_constraint("ck_managed_documents_paper_status", "managed_documents", type_="check")
    op.drop_constraint("ck_managed_documents_signature_method", "managed_documents", type_="check")
    for column in (
        "paper_evidence_uploaded_by", "paper_evidence_uploaded_at", "paper_evidence_file_name",
        "paper_evidence_content_type", "paper_evidence_sha256", "paper_evidence_storage_key",
        "paper_signed_received_by", "paper_signed_received_at", "paper_printed_by",
        "paper_printed_at", "paper_status", "signature_method",
    ):
        op.drop_column("managed_documents", column)
