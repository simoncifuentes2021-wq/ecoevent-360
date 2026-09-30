"""Move public waste access to one event form and configure materials per point.

Revision ID: 20260930_0067
Revises: 20260930_0066
"""
from collections.abc import Sequence
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260930_0067"
down_revision: str | None = "20260930_0066"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "event_waste_public_forms",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token", sa.String(96), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="DRAFT"),
        sa.Column("opened_at", sa.DateTime(timezone=True)),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint("status in ('DRAFT','ACTIVE','CLOSED')", name="ck_event_waste_public_forms_status"),
        sa.UniqueConstraint("event_id", name="uq_event_waste_public_forms_event_id"),
        sa.UniqueConstraint("token", name="uq_event_waste_public_forms_token"),
    )
    op.create_table(
        "waste_collection_point_types",
        sa.Column("collection_point_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("waste_collection_points.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("waste_type_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("waste_types.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    # Existing local flows accepted every waste type at each point. Preserve that
    # behavior while moving QR ownership to a single event token.
    op.execute("""
        INSERT INTO waste_collection_point_types (collection_point_id, waste_type_id)
        SELECT p.id, wt.id FROM waste_collection_points p CROSS JOIN waste_types wt
        ON CONFLICT DO NOTHING
    """)
    op.execute("""
        INSERT INTO event_waste_public_forms (event_id, token, status, opened_at)
        SELECT DISTINCT p.event_id, md5(random()::text || clock_timestamp()::text) || md5(random()::text || clock_timestamp()::text), 'ACTIVE', NOW()
        FROM waste_collection_points p
        ON CONFLICT (event_id) DO NOTHING
    """)
    op.execute("ALTER TABLE waste_collection_point_types ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE event_waste_public_forms ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE OR REPLACE FUNCTION app_public_waste_token_valid()
        RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
          SELECT EXISTS (SELECT 1 FROM event_waste_public_forms f
            WHERE f.status IN ('ACTIVE','CLOSED') AND f.token = nullif(current_setting('app.public_waste_token', true), ''))
        $$
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION app_public_waste_point_access(point_uuid uuid, event_uuid uuid DEFAULT NULL)
        RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
          SELECT EXISTS (SELECT 1 FROM waste_collection_points p
            JOIN event_waste_public_forms f ON f.event_id = p.event_id
            WHERE p.id = point_uuid AND p.is_active AND f.status = 'ACTIVE'
              AND f.status IN ('ACTIVE','CLOSED') AND f.token = nullif(current_setting('app.public_waste_token', true), '')
              AND (event_uuid IS NULL OR p.event_id = event_uuid))
        $$
    """)
    op.execute("DROP POLICY IF EXISTS waste_collection_points_event_access ON waste_collection_points")
    op.execute("""
        CREATE POLICY waste_collection_points_event_access ON waste_collection_points
        FOR ALL USING (app_can_view_event(event_id) OR app_public_waste_point_access(id, event_id))
        WITH CHECK (app_can_view_event(event_id))
    """)
    op.execute("DROP POLICY IF EXISTS events_public_waste_read ON events")
    op.execute("""
        CREATE POLICY events_public_waste_read ON events FOR SELECT USING (
          EXISTS (SELECT 1 FROM event_waste_public_forms f WHERE f.event_id=events.id
            AND f.status IN ('ACTIVE','CLOSED') AND f.token=nullif(current_setting('app.public_waste_token', true), '')))
    """)
    op.execute("DROP POLICY IF EXISTS waste_types_public_waste_read ON waste_types")
    op.execute("""
        CREATE POLICY waste_types_public_waste_read ON waste_types FOR SELECT USING (
          app_public_waste_token_valid() AND EXISTS (
            SELECT 1 FROM waste_collection_point_types pt JOIN waste_collection_points p ON p.id=pt.collection_point_id
            JOIN event_waste_public_forms f ON f.event_id=p.event_id
            WHERE pt.waste_type_id=waste_types.id AND p.is_active
              AND f.token=nullif(current_setting('app.public_waste_token', true), '')))
    """)
    op.execute("""
        CREATE POLICY waste_collection_point_types_public_read ON waste_collection_point_types
        FOR SELECT USING (app_public_waste_point_access(collection_point_id, NULL))
    """)
    op.execute("""
        CREATE POLICY event_waste_public_forms_event_access ON event_waste_public_forms
        FOR ALL USING (app_can_view_event(event_id) OR (status IN ('ACTIVE','CLOSED') AND token=nullif(current_setting('app.public_waste_token', true), '')))
        WITH CHECK (app_can_view_event(event_id))
    """)
    for policy in ("waste_collection_records_public_read", "waste_collection_records_public_insert"):
        op.execute(f"DROP POLICY IF EXISTS {policy} ON waste_collection_records")
    op.execute("""
        CREATE POLICY waste_collection_records_public_read ON waste_collection_records FOR SELECT USING (
          EXISTS (SELECT 1 FROM waste_collection_points p WHERE p.id=collection_point_id
            AND app_public_waste_point_access(p.id, waste_collection_records.event_id)))
    """)
    op.execute("""
        CREATE POLICY waste_collection_records_public_insert ON waste_collection_records FOR INSERT WITH CHECK (
          client_generated_id IS NOT NULL AND EXISTS (SELECT 1 FROM waste_collection_points p
            WHERE p.id=collection_point_id AND p.event_id=waste_collection_records.event_id
              AND app_public_waste_point_access(p.id, waste_collection_records.event_id)))
    """)


def downgrade() -> None:
    for policy, table in (
        ("waste_collection_records_public_read", "waste_collection_records"),
        ("waste_collection_records_public_insert", "waste_collection_records"),
        ("waste_collection_point_types_public_read", "waste_collection_point_types"),
        ("event_waste_public_forms_event_access", "event_waste_public_forms"),
    ):
        op.execute(f"DROP POLICY IF EXISTS {policy} ON {table}")
    op.execute("DROP POLICY IF EXISTS events_public_waste_read ON events")
    op.execute("DROP POLICY IF EXISTS waste_types_public_waste_read ON waste_types")
    op.drop_table("waste_collection_point_types")
    op.drop_table("event_waste_public_forms")
    # Legacy QR tokens remain on collection points, but re-create old policy helpers.
    op.execute("""
        CREATE OR REPLACE FUNCTION app_public_waste_point_access(point_uuid uuid, event_uuid uuid DEFAULT NULL)
        RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
          SELECT EXISTS (SELECT 1 FROM waste_collection_points p WHERE p.id=point_uuid AND p.is_active
            AND (event_uuid IS NULL OR p.event_id=event_uuid)
            AND p.qr_token=nullif(current_setting('app.public_waste_token', true),''))
        $$
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION app_public_waste_token_valid()
        RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
          SELECT EXISTS (SELECT 1 FROM waste_collection_points p WHERE p.is_active
            AND p.qr_token=nullif(current_setting('app.public_waste_token', true),''))
        $$
    """)
