"""Group signature requests so paired PDFs are delivered together."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20261019_0083"
down_revision: str | None = "20261014_0082"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "document_signature_requests",
        sa.Column("bundle_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "idx_document_signature_requests_bundle",
        "document_signature_requests",
        ["bundle_id"],
    )
    op.execute("drop policy if exists managed_documents_public_read on managed_documents")
    op.execute("drop policy if exists document_signature_requests_select on document_signature_requests")
    op.execute("drop policy if exists document_signature_requests_update on document_signature_requests")
    op.execute("""
        create or replace function app_public_document_bundle_id() returns uuid
        language sql stable security definer set search_path = public as $$
            select r.bundle_id from document_signature_requests r
            where r.token_hash = nullif(current_setting('app.public_document_token_hash', true), '')
              and r.bundle_id is not null and r.revoked_at is null and r.expires_at > now()
            limit 1
        $$
    """)
    op.execute("""
        create or replace function app_public_document_bundle_document_ids()
        returns setof uuid language sql stable security definer set search_path = public as $$
            select r.document_id from document_signature_requests r
            where app_public_document_signature_valid()
              and r.bundle_id = app_public_document_bundle_id()
              and r.revoked_at is null and r.expires_at > now()
        $$
    """)
    op.execute("""
        create policy managed_documents_public_read on managed_documents for select
        using (id = app_public_document_id()
            or id in (select app_public_document_bundle_document_ids()))
    """)
    op.execute("""
        create policy document_signature_requests_select on document_signature_requests for select
        using ((app_public_document_signature_valid() and token_hash =
            nullif(current_setting('app.public_document_token_hash', true), ''))
            or (app_public_document_bundle_id() is not null
                and bundle_id = app_public_document_bundle_id()
                and revoked_at is null and expires_at > now())
            or app_documents_can_access_document(document_id) or exists (
                select 1 from managed_documents d where d.id = document_signature_requests.document_id
                  and app_documents_can_access_event(d.event_id, d.client_id)))
    """)
    op.execute("""
        create policy document_signature_requests_update on document_signature_requests for update
        using (((app_public_document_signature_valid() and token_hash =
            nullif(current_setting('app.public_document_token_hash', true), '')
            and document_id = app_public_document_id())
            or (app_public_document_bundle_id() is not null
                and bundle_id = app_public_document_bundle_id()
                and revoked_at is null and expires_at > now())
            or app_documents_can_access_document(document_id) or exists (
                select 1 from managed_documents d where d.id = document_signature_requests.document_id
                  and app_documents_can_access_event(d.event_id, d.client_id))))
        with check (((app_public_document_signature_valid() and token_hash =
            nullif(current_setting('app.public_document_token_hash', true), '')
            and document_id = app_public_document_id())
            or (app_public_document_bundle_id() is not null
                and bundle_id = app_public_document_bundle_id()
                and revoked_at is null and expires_at > now())
            or app_documents_can_access_document(document_id) or exists (
                select 1 from managed_documents d where d.id = document_signature_requests.document_id
                  and app_documents_can_access_event(d.event_id, d.client_id))))
    """)


def downgrade() -> None:
    op.execute("drop policy if exists document_signature_requests_update on document_signature_requests")
    op.execute("drop policy if exists document_signature_requests_select on document_signature_requests")
    op.execute("drop policy if exists managed_documents_public_read on managed_documents")
    op.execute("drop function if exists app_public_document_bundle_document_ids()")
    op.execute("drop function if exists app_public_document_bundle_id()")
    op.execute("""
        create policy managed_documents_public_read on managed_documents for select
        using (id = app_public_document_id())
    """)
    op.execute("""
        create policy document_signature_requests_select on document_signature_requests for select
        using (app_public_document_signature_valid() and token_hash =
            nullif(current_setting('app.public_document_token_hash', true), '')
            or app_documents_can_access_document(document_id) or exists (
                select 1 from managed_documents d where d.id = document_signature_requests.document_id
                  and app_documents_can_access_event(d.event_id, d.client_id)))
    """)
    op.execute("""
        create policy document_signature_requests_update on document_signature_requests for update
        using ((app_public_document_signature_valid() and token_hash =
            nullif(current_setting('app.public_document_token_hash', true), '')
            and document_id = app_public_document_id())
            or app_documents_can_access_document(document_id) or exists (
                select 1 from managed_documents d where d.id = document_signature_requests.document_id
                  and app_documents_can_access_event(d.event_id, d.client_id)))
        with check ((app_public_document_signature_valid() and token_hash =
            nullif(current_setting('app.public_document_token_hash', true), '')
            and document_id = app_public_document_id())
            or app_documents_can_access_document(document_id) or exists (
                select 1 from managed_documents d where d.id = document_signature_requests.document_id
                  and app_documents_can_access_event(d.event_id, d.client_id)))
    """)
    op.drop_index("idx_document_signature_requests_bundle", table_name="document_signature_requests")
    op.drop_column("document_signature_requests", "bundle_id")
