"""Add event waste collection points and public submission metadata.

Revision ID: 20260929_0065
Revises: 20260922_0064
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260929_0065"
down_revision: str | None = "20260922_0064"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "waste_collection_points",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("zone_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("event_zones.id", ondelete="SET NULL")),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("location_description", sa.Text()),
        sa.Column("capacity_kg", sa.Numeric(12, 3)),
        sa.Column("qr_token", sa.String(96), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("event_id", "code", name="uq_waste_collection_points_event_code"),
        sa.UniqueConstraint("qr_token", name="uq_waste_collection_points_qr_token"),
        sa.CheckConstraint("capacity_kg is null or capacity_kg >= 0", name="ck_waste_collection_points_capacity"),
    )
    op.create_index("idx_waste_collection_points_event_id", "waste_collection_points", ["event_id"])
    op.add_column("waste_records", sa.Column("collection_point_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("waste_records", sa.Column("submitter_name", sa.String(160), nullable=True))
    op.add_column("waste_records", sa.Column("submitter_rut", sa.String(20), nullable=True))
    op.add_column("waste_records", sa.Column("client_generated_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("waste_records", sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("waste_records", sa.Column("submission_source", sa.String(20), nullable=False, server_default="INTERNAL"))
    op.add_column("waste_records", sa.Column("synced_at", sa.DateTime(), nullable=True))
    op.create_foreign_key("fk_waste_records_collection_point_id", "waste_records", "waste_collection_points", ["collection_point_id"], ["id"], ondelete="SET NULL")
    op.create_check_constraint("ck_waste_records_submission_source", "waste_records", "submission_source in ('INTERNAL', 'PUBLIC_FORM')")
    op.create_index("idx_waste_records_collection_point_id", "waste_records", ["collection_point_id"])
    op.create_unique_constraint("uq_waste_records_client_generated_id", "waste_records", ["client_generated_id"])

    op.execute("alter table waste_collection_points enable row level security")
    op.execute("""
        create or replace function app_public_waste_point_access(point_uuid uuid, event_uuid uuid default null)
        returns boolean language sql stable security definer set search_path = public as $$
            select exists (select 1 from waste_collection_points p where p.id = point_uuid
                and p.is_active and (event_uuid is null or p.event_id = event_uuid)
                and p.qr_token = nullif(current_setting('app.public_waste_token', true), ''))
        $$
    """)
    op.execute("""
        create or replace function app_public_waste_token_valid()
        returns boolean language sql stable security definer set search_path = public as $$
            select exists (select 1 from waste_collection_points p where p.is_active
                and p.qr_token = nullif(current_setting('app.public_waste_token', true), ''))
        $$
    """)
    op.execute("""
        create policy waste_collection_points_event_access on waste_collection_points
        for all
        using (app_can_view_event(event_id) or app_public_waste_point_access(id, event_id))
        with check (app_can_view_event(event_id))
    """)
    op.execute("""
        create policy events_public_waste_read on events for select using (
            exists (select 1 from waste_collection_points p where p.event_id = events.id
                and app_public_waste_point_access(p.id, events.id))
        )
    """)
    op.execute("""
        create policy waste_types_public_waste_read on waste_types for select using (
            app_public_waste_token_valid()
        )
    """)
    op.execute("""
        create policy waste_records_public_waste_insert on waste_records for insert with check (
            submission_source = 'PUBLIC_FORM' and client_generated_id is not null
            and exists (select 1 from waste_collection_points p
                where p.id = collection_point_id and app_public_waste_point_access(p.id, event_id))
        )
    """)
    op.execute("""
        create policy waste_records_public_waste_read on waste_records for select using (
            submission_source = 'PUBLIC_FORM' and exists (select 1 from waste_collection_points p
                where p.id = collection_point_id and app_public_waste_point_access(p.id))
        )
    """)


def downgrade() -> None:
    op.execute("drop policy if exists waste_records_public_waste_read on waste_records")
    op.execute("drop policy if exists waste_records_public_waste_insert on waste_records")
    op.execute("drop policy if exists waste_types_public_waste_read on waste_types")
    op.execute("drop policy if exists events_public_waste_read on events")
    op.execute("drop policy if exists waste_collection_points_event_access on waste_collection_points")
    op.execute("drop function if exists app_public_waste_point_access(uuid, uuid)")
    op.execute("drop function if exists app_public_waste_token_valid()")
    op.drop_constraint("uq_waste_records_client_generated_id", "waste_records", type_="unique")
    op.drop_index("idx_waste_records_collection_point_id", table_name="waste_records")
    op.drop_constraint("ck_waste_records_submission_source", "waste_records", type_="check")
    op.drop_constraint("fk_waste_records_collection_point_id", "waste_records", type_="foreignkey")
    for column in ("synced_at", "submission_source", "device_id", "client_generated_id", "submitter_rut", "submitter_name", "collection_point_id"):
        op.drop_column("waste_records", column)
    op.drop_index("idx_waste_collection_points_event_id", table_name="waste_collection_points")
    op.drop_table("waste_collection_points")
