"""Make worker identities global to Greenway; keep engagements event-scoped.

Revision ID: 20261006_0079
Revises: 20261006_0078
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20261006_0079"
down_revision: str | None = "20261006_0078"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Merge duplicate client-owned identities by normalized RUT without losing
    # historical event assignments or documents.
    op.execute("""
        create temporary table document_person_merge on commit drop as
        with ranked as (
            select id, first_value(id) over (
                partition by rut_normalized order by created_at, id
            ) as canonical_id,
            row_number() over (
                partition by rut_normalized order by created_at, id
            ) as row_num
            from document_people
        )
        select id as duplicate_id, canonical_id
        from ranked where row_num > 1
    """)
    op.execute("""
        with latest_duplicate as (
            select distinct on (merged.canonical_id)
                merged.canonical_id, duplicate.first_name, duplicate.last_name,
                duplicate.rut, duplicate.email, duplicate.phone, duplicate.address,
                duplicate.commune, duplicate.updated_at
            from document_person_merge merged
            join document_people duplicate on duplicate.id = merged.duplicate_id
            order by merged.canonical_id, duplicate.updated_at desc, duplicate.id
        )
        update document_people canonical
        set first_name = coalesce(nullif(trim(latest.first_name), ''), canonical.first_name),
            last_name = coalesce(nullif(trim(latest.last_name), ''), canonical.last_name),
            rut = coalesce(nullif(trim(latest.rut), ''), canonical.rut),
            email = coalesce(nullif(trim(latest.email), ''), canonical.email),
            phone = coalesce(nullif(trim(latest.phone), ''), canonical.phone),
            address = coalesce(nullif(trim(latest.address), ''), canonical.address),
            commune = coalesce(nullif(trim(latest.commune), ''), canonical.commune),
            updated_at = greatest(canonical.updated_at, latest.updated_at)
        from latest_duplicate latest
        where canonical.id = latest.canonical_id
    """)
    op.execute("""
        update document_employments assignment
        set person_id = merged.canonical_id
        from document_person_merge merged
        where assignment.person_id = merged.duplicate_id
    """)
    op.execute("""
        update managed_documents document
        set person_id = merged.canonical_id
        from document_person_merge merged
        where document.person_id = merged.duplicate_id
    """)
    op.execute("""
        delete from document_people person using document_person_merge merged
        where person.id = merged.duplicate_id
    """)

    op.drop_index("uq_document_people_client_email", table_name="document_people")
    op.drop_index("idx_document_people_client_name", table_name="document_people")
    op.drop_constraint(
        "uq_document_people_client_rut", "document_people", type_="unique"
    )
    # Keep this nullable legacy field temporarily for safe rollback and old
    # snapshots; it no longer defines identity or authorization.
    op.execute("update document_people set client_id = null")
    op.alter_column("document_people", "client_id", nullable=True)
    op.create_unique_constraint(
        "uq_document_people_rut", "document_people", ["rut_normalized"]
    )
    op.create_index(
        "idx_document_people_email",
        "document_people",
        [sa.text("lower(email)")],
        postgresql_where="email is not null",
    )
    op.create_index(
        "idx_document_people_name", "document_people", ["last_name", "first_name"]
    )

    op.execute("drop policy document_people_scope on document_people")
    op.execute("""
        create or replace function app_document_person_lookup_id() returns uuid
        language sql stable security definer set search_path = public as $$
            select person.id from document_people person
            where person.rut_normalized = nullif(
                current_setting('app.document_person_lookup_rut', true), ''
            )
              and app_current_role() = 'SUPERVISOR'
              and app_document_event_client_id() is not null
            limit 1
        $$
    """)
    op.execute("""
        create policy document_people_scope on document_people for all
        using (
            app_current_role() in ('SUPER_ADMIN', 'ADMIN')
            or document_people.id = app_document_person_lookup_id()
            or exists (
                select 1 from document_employments assignment
                where assignment.person_id = document_people.id
                  and app_documents_can_access_event(
                      assignment.event_id, assignment.client_id
                  )
            )
        )
        with check (
            app_current_role() in ('SUPER_ADMIN', 'ADMIN')
            or document_people.id = app_document_person_lookup_id()
            or app_document_event_client_id() is not null
        )
    """)


def downgrade() -> None:
    op.execute("drop policy document_people_scope on document_people")
    op.execute("drop function if exists app_document_person_lookup_id()")
    op.execute("""
        update document_people person
        set client_id = (
            select assignment.client_id from document_employments assignment
            where assignment.person_id = person.id
            order by assignment.created_at, assignment.id limit 1
        )
    """)
    op.execute("""
        update document_people person
        set client_id = (
            select client_id from clients order by created_at, id limit 1
        )
        where client_id is null
    """)
    op.alter_column("document_people", "client_id", nullable=False)
    op.drop_index("idx_document_people_name", table_name="document_people")
    op.drop_index("idx_document_people_email", table_name="document_people")
    op.drop_constraint("uq_document_people_rut", "document_people", type_="unique")
    op.create_unique_constraint(
        "uq_document_people_client_rut",
        "document_people",
        ["client_id", "rut_normalized"],
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
        postgresql_where="email is not null",
    )
    op.execute("""
        create policy document_people_scope on document_people for all
        using (app_documents_can_access_client(client_id) or exists (
            select 1 from document_employments assignment
            where assignment.person_id = document_people.id
              and app_documents_can_access_event(assignment.event_id, assignment.client_id)
              and assignment.client_id = document_people.client_id
        ))
        with check (app_documents_can_access_client(client_id)
            or client_id = app_document_event_client_id())
    """)
