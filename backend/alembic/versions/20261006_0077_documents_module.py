"""Add private document management, external people and EPP registers.

Revision ID: 20261006_0077
Revises: 20261003_0076
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20261006_0077"
down_revision: str | None = "20261003_0076"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_people",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clients.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(120), nullable=False),
        sa.Column("rut", sa.String(16), nullable=False),
        sa.Column("rut_normalized", sa.String(12), nullable=False),
        sa.Column("email", sa.String(180)),
        sa.Column("phone", sa.String(40)),
        sa.Column("address", sa.String(240)),
        sa.Column("commune", sa.String(120)),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("client_id", "rut_normalized", name="uq_document_people_client_rut"),
    )
    op.create_index(
        "idx_document_people_client_name",
        "document_people",
        ["client_id", "last_name", "first_name"],
    )
    op.create_index(
        "uq_document_people_client_email",
        "document_people",
        ["client_id", sa.text("lower(email)")],
        unique=True,
        postgresql_where=sa.text("email is not null"),
    )

    op.create_table(
        "document_employments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clients.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "person_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("document_people.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("events.id", ondelete="SET NULL"),
        ),
        sa.Column("position", sa.String(160), nullable=False),
        sa.Column("area", sa.String(120)),
        sa.Column("start_date", sa.Date()),
        sa.Column("end_date", sa.Date()),
        sa.Column("remuneration", sa.Numeric(12, 2)),
        sa.Column("workplace", sa.String(240)),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint(
            "end_date is null or start_date is null or end_date >= start_date",
            name="ck_document_employments_dates",
        ),
    )
    op.create_index(
        "idx_document_employments_person", "document_employments", ["person_id", "created_at"]
    )
    op.create_index("idx_document_employments_event", "document_employments", ["event_id"])

    op.create_table(
        "managed_documents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clients.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "person_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("document_people.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "employment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("document_employments.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("events.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "supersedes_document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("managed_documents.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="DRAFT"),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column(
            "data", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column("frozen_snapshot", postgresql.JSONB()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("original_pdf_key", sa.String(420)),
        sa.Column("signed_pdf_key", sa.String(420)),
        sa.Column("original_sha256", sa.String(64)),
        sa.Column("signed_sha256", sa.String(64)),
        sa.Column("completed_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint("kind in ('CONTRACT', 'EPP')", name="ck_managed_documents_kind"),
        sa.CheckConstraint(
            "status in ('DRAFT', 'READY', 'SENT', 'VIEWED', 'PARTIALLY_SIGNED', 'COMPLETED', 'CANCELLED', 'EXPIRED', 'SUPERSEDED')",
            name="ck_managed_documents_status",
        ),
    )
    op.create_index(
        "idx_managed_documents_client_status",
        "managed_documents",
        ["client_id", "status", "updated_at"],
    )
    op.create_index("idx_managed_documents_event", "managed_documents", ["event_id"])
    op.create_index("idx_managed_documents_person", "managed_documents", ["person_id"])

    op.create_table(
        "epp_deliveries",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clients.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("managed_documents.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("riohs_received", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("eirl_completed", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("delivery_date", sa.Date()),
        sa.Column(
            "supervisor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index(
        "idx_epp_deliveries_client_flags",
        "epp_deliveries",
        ["client_id", "riohs_received", "eirl_completed"],
    )
    op.create_table(
        "epp_delivery_items",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "delivery_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("epp_deliveries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("item_code", sa.String(40), nullable=False),
        sa.Column("label", sa.String(100), nullable=False),
        sa.Column("received_at", sa.Date()),
        sa.Column("returned_at", sa.Date()),
        sa.Column(
            "received_conformity", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")
        ),
        sa.UniqueConstraint("delivery_id", "item_code", name="uq_epp_delivery_items_code"),
        sa.CheckConstraint(
            "returned_at is null or received_at is null or returned_at >= received_at",
            name="ck_epp_delivery_items_dates",
        ),
    )
    op.create_table(
        "document_signature_requests",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clients.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("managed_documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime()),
        sa.Column("opened_at", sa.DateTime()),
        sa.Column("worker_signed_at", sa.DateTime()),
        sa.Column("worker_signed_name", sa.String(180)),
        sa.Column("supervisor_signed_at", sa.DateTime()),
        sa.Column(
            "supervisor_signed_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "signature_provider", sa.String(32), nullable=False, server_default="LOCAL_SIMULATED"
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("token_hash", name="uq_document_signature_requests_token_hash"),
    )
    op.create_index(
        "idx_document_signature_requests_document",
        "document_signature_requests",
        ["document_id", "created_at"],
    )
    op.create_index(
        "idx_document_signature_requests_expiry", "document_signature_requests", ["expires_at"]
    )

    op.execute("""
        create or replace function app_public_document_signature_valid() returns boolean
        language sql stable security definer set search_path = public as $$
            select exists (select 1 from document_signature_requests r
                where r.token_hash = nullif(current_setting('app.public_document_token_hash', true), '')
                  and r.revoked_at is null and r.expires_at > now())
        $$
    """)
    op.execute("""
        create or replace function app_public_document_id() returns uuid
        language sql stable security definer set search_path = public as $$
            select r.document_id from document_signature_requests r
            where r.token_hash = nullif(current_setting('app.public_document_token_hash', true), '')
              and r.revoked_at is null and r.expires_at > now() limit 1
        $$
    """)
    op.execute("""
        create or replace function app_public_document_person_id() returns uuid
        language sql stable security definer set search_path = public as $$
            select d.person_id from managed_documents d where d.id = app_public_document_id()
        $$
    """)
    op.execute("""
        create or replace function app_document_event_client_id() returns uuid
        language sql stable security definer set search_path = public as $$
            select e.client_id from events e
            where e.id = nullif(current_setting('app.document_event_id', true), '')::uuid
              and app_current_role() = 'SUPERVISOR' and app_can_view_event(e.id)
            limit 1
        $$
    """)
    op.execute("""
        create or replace function app_documents_can_access_client(target_client_id uuid)
        returns boolean language sql stable security definer set search_path = public as $$
            select app_current_role() = 'SUPER_ADMIN'
                or (app_current_role() = 'ADMIN'
                    and app_current_client_id() = target_client_id)
        $$
    """)
    op.execute("""
        create or replace function app_documents_can_access_event(
            target_event_id uuid, target_client_id uuid
        ) returns boolean language sql stable security definer set search_path = public as $$
            select exists (
                select 1 from events e
                where e.id = target_event_id and e.client_id = target_client_id
                  and app_current_role() = 'SUPERVISOR' and app_can_view_event(e.id)
            )
        $$
    """)
    op.execute("""
        create or replace function app_documents_can_access_document(target_document_id uuid)
        returns boolean language sql stable security definer set search_path = public as $$
            select exists (
                select 1 from managed_documents d
                where d.id = target_document_id
                  and (app_documents_can_access_client(d.client_id)
                    or app_documents_can_access_event(d.event_id, d.client_id))
            )
        $$
    """)
    op.execute("""
        create or replace function app_record_public_document_audit(
            target_document_id uuid, target_action text
        ) returns void language plpgsql security definer set search_path = public as $$
        declare
            target_client_id uuid;
            target_event_id uuid;
        begin
            if target_action not in ('DOCUMENT_PUBLIC_OPENED', 'DOCUMENT_WORKER_SIGNED')
               or target_document_id is distinct from app_public_document_id() then
                raise exception 'invalid public document audit event';
            end if;
            if target_action = 'DOCUMENT_PUBLIC_OPENED' and not exists (
                select 1 from document_signature_requests r
                where r.token_hash = nullif(current_setting('app.public_document_token_hash', true), '')
                  and r.document_id = target_document_id and r.opened_at is not null
                  and r.revoked_at is null and r.expires_at > now()
            ) then
                raise exception 'document has not been opened with a valid capability';
            end if;
            if target_action = 'DOCUMENT_WORKER_SIGNED' and not exists (
                select 1 from document_signature_requests r
                where r.token_hash = nullif(current_setting('app.public_document_token_hash', true), '')
                  and r.document_id = target_document_id and r.worker_signed_at is not null
                  and r.revoked_at is null and r.expires_at > now()
            ) then
                raise exception 'document has not been signed with a valid capability';
            end if;
            select d.client_id, d.event_id into target_client_id, target_event_id
              from managed_documents d where d.id = target_document_id;
            if target_client_id is null then
                raise exception 'document not found';
            end if;
            insert into audit_logs (
                user_id, client_id, event_id, action, module, entity_type, entity_id,
                status, metadata, created_at
            ) values (
                null, target_client_id, target_event_id, target_action, 'documents',
                'ManagedDocument', target_document_id, 'SUCCESS',
                jsonb_build_object('source', 'public_portal'), now()
            );
        end
        $$
    """)
    for table in (
        "document_people",
        "document_employments",
        "managed_documents",
        "epp_deliveries",
        "epp_delivery_items",
        "document_signature_requests",
    ):
        op.execute(f"alter table {table} enable row level security")

    op.execute("""
        create policy document_people_scope on document_people for all
        using (app_documents_can_access_client(client_id) or exists (
            select 1 from document_employments a where a.person_id = document_people.id
              and app_documents_can_access_event(a.event_id, a.client_id)
              and a.client_id = document_people.client_id))
        with check (app_documents_can_access_client(client_id)
            or client_id = app_document_event_client_id())
    """)
    op.execute("""
        create policy document_people_public_read on document_people for select
        using (id = app_public_document_person_id())
    """)
    op.execute("""
        create policy document_employments_scope on document_employments for all
        using (app_documents_can_access_client(client_id)
            or app_documents_can_access_event(event_id, client_id))
        with check (app_documents_can_access_client(client_id)
            or app_documents_can_access_event(event_id, client_id))
    """)
    op.execute("""
        create policy managed_documents_scope on managed_documents for all
        using (app_documents_can_access_client(client_id)
            or app_documents_can_access_event(event_id, client_id))
        with check (app_documents_can_access_client(client_id)
            or app_documents_can_access_event(event_id, client_id))
    """)
    op.execute("""
        create policy managed_documents_public_read on managed_documents for select
        using (id = app_public_document_id())
    """)
    op.execute("""
        create policy epp_deliveries_read on epp_deliveries for select
        using (document_id = app_public_document_id()
            or app_documents_can_access_document(document_id))
    """)
    op.execute("""
        create policy epp_deliveries_write on epp_deliveries for all
        using (app_documents_can_access_document(document_id))
        with check (app_documents_can_access_document(document_id))
    """)
    op.execute("""
        create policy epp_delivery_items_read on epp_delivery_items for select
        using (
            exists (
                select 1 from epp_deliveries e
                where e.id = epp_delivery_items.delivery_id
                  and e.document_id = app_public_document_id()
            )
            or exists (
                select 1 from epp_deliveries e
                where e.id = epp_delivery_items.delivery_id
                  and app_documents_can_access_document(e.document_id)
            )
        )
    """)
    op.execute("""
        create policy epp_delivery_items_write on epp_delivery_items for all
        using (exists (select 1 from epp_deliveries e
            where e.id = epp_delivery_items.delivery_id
              and app_documents_can_access_document(e.document_id)))
        with check (exists (select 1 from epp_deliveries e
            where e.id = epp_delivery_items.delivery_id
              and app_documents_can_access_document(e.document_id)))
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
        create policy document_signature_requests_insert on document_signature_requests for insert
        with check (app_documents_can_access_document(document_id) or exists (
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


def downgrade() -> None:
    for table, policy in (
        ("document_signature_requests", "document_signature_requests_update"),
        ("document_signature_requests", "document_signature_requests_insert"),
        ("document_signature_requests", "document_signature_requests_select"),
        ("epp_delivery_items", "epp_delivery_items_write"),
        ("epp_delivery_items", "epp_delivery_items_read"),
        ("epp_deliveries", "epp_deliveries_write"),
        ("epp_deliveries", "epp_deliveries_read"),
        ("managed_documents", "managed_documents_scope"),
        ("managed_documents", "managed_documents_public_read"),
        ("document_employments", "document_employments_scope"),
        ("document_people", "document_people_scope"),
        ("document_people", "document_people_public_read"),
    ):
        op.execute(f"drop policy if exists {policy} on {table}")
    op.execute("drop function if exists app_public_document_signature_valid()")
    op.execute("drop function if exists app_public_document_person_id()")
    op.execute("drop function if exists app_public_document_id()")
    op.execute("drop function if exists app_document_event_client_id()")
    op.execute("drop function if exists app_record_public_document_audit(uuid, text)")
    op.execute("drop function if exists app_documents_can_access_document(uuid)")
    op.execute("drop function if exists app_documents_can_access_event(uuid, uuid)")
    op.execute("drop function if exists app_documents_can_access_client(uuid)")
    op.drop_table("document_signature_requests")
    op.drop_table("epp_delivery_items")
    op.drop_index("idx_epp_deliveries_client_flags", table_name="epp_deliveries")
    op.drop_table("epp_deliveries")
    op.drop_index("idx_managed_documents_person", table_name="managed_documents")
    op.drop_index("idx_managed_documents_event", table_name="managed_documents")
    op.drop_index("idx_managed_documents_client_status", table_name="managed_documents")
    op.drop_table("managed_documents")
    op.drop_index("idx_document_employments_event", table_name="document_employments")
    op.drop_index("idx_document_employments_person", table_name="document_employments")
    op.drop_table("document_employments")
    op.drop_index("idx_document_people_client_name", table_name="document_people")
    op.drop_index("uq_document_people_client_email", table_name="document_people")
    op.drop_table("document_people")
