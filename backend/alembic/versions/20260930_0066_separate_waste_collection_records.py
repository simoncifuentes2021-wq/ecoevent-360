"""Separate public collection submissions from environmental waste records.

Revision ID: 20260930_0066
Revises: 20260929_0065
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260930_0066"
down_revision: str | None = "20260929_0065"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
          IF EXISTS (
            SELECT 1 FROM waste_records wr
            WHERE (wr.submission_source = 'PUBLIC_FORM' OR wr.collection_point_id IS NOT NULL)
              AND (wr.collection_point_id IS NULL OR wr.waste_type_id IS NULL
                OR wr.client_generated_id IS NULL OR wr.submitter_name IS NULL
                OR wr.submitter_rut IS NULL OR wr.weight_kg <= 0
                OR NOT EXISTS (SELECT 1 FROM waste_collection_points p
                    WHERE p.id = wr.collection_point_id AND p.event_id = wr.event_id))
          ) THEN
            RAISE EXCEPTION 'Cannot migrate incomplete or mismatched public waste records';
          END IF;
        END $$;
    """)
    op.create_table(
        "waste_collection_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("collection_point_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("waste_collection_points.id", ondelete="CASCADE"), nullable=False),
        sa.Column("waste_type_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("waste_types.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("weight_kg", sa.Numeric(12, 3), nullable=False),
        sa.Column("submitter_name", sa.String(160), nullable=False),
        sa.Column("submitter_rut", sa.String(20), nullable=False),
        sa.Column("client_generated_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint("weight_kg > 0", name="ck_waste_collection_records_weight_positive"),
        sa.UniqueConstraint("client_generated_id", name="uq_waste_collection_records_client_generated_id"),
    )
    op.create_index("idx_waste_collection_records_event_id", "waste_collection_records", ["event_id"])
    op.create_index("idx_waste_collection_records_point_id", "waste_collection_records", ["collection_point_id"])
    op.create_index("idx_waste_collection_records_type_id", "waste_collection_records", ["waste_type_id"])
    op.create_index("idx_waste_collection_records_recorded_at", "waste_collection_records", ["recorded_at"])
    op.execute("""
        INSERT INTO waste_collection_records (
            id, event_id, collection_point_id, waste_type_id, weight_kg, submitter_name,
            submitter_rut, client_generated_id, device_id, recorded_at, synced_at, created_at
        )
        SELECT wr.id, wr.event_id, wr.collection_point_id, wr.waste_type_id, wr.weight_kg,
            wr.submitter_name, wr.submitter_rut, wr.client_generated_id, wr.device_id,
            wr.recorded_at AT TIME ZONE 'UTC', wr.synced_at AT TIME ZONE 'UTC', wr.created_at
        FROM waste_records wr
        WHERE wr.submission_source = 'PUBLIC_FORM' OR wr.collection_point_id IS NOT NULL
        ON CONFLICT (client_generated_id) DO NOTHING
    """)

    op.execute("DROP POLICY IF EXISTS waste_records_public_waste_read ON waste_records")
    op.execute("DROP POLICY IF EXISTS waste_records_public_waste_insert ON waste_records")
    op.drop_constraint("uq_waste_records_client_generated_id", "waste_records", type_="unique")
    op.drop_index("idx_waste_records_collection_point_id", table_name="waste_records")
    op.drop_constraint("ck_waste_records_submission_source", "waste_records", type_="check")
    op.drop_constraint("fk_waste_records_collection_point_id", "waste_records", type_="foreignkey")
    for column in ("synced_at", "submission_source", "device_id", "client_generated_id", "submitter_rut", "submitter_name", "collection_point_id"):
        op.drop_column("waste_records", column)

    op.execute("ALTER TABLE waste_collection_records ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY waste_collection_records_event_access ON waste_collection_records
        FOR ALL USING (app_can_view_event(event_id))
        WITH CHECK (app_can_view_event(event_id))
    """)
    op.execute("""
        CREATE POLICY waste_collection_records_public_read ON waste_collection_records
        FOR SELECT USING (EXISTS (
            SELECT 1 FROM waste_collection_points p
            WHERE p.id = collection_point_id
              AND app_public_waste_point_access(p.id, waste_collection_records.event_id)
        ))
    """)
    op.execute("""
        CREATE POLICY waste_collection_records_public_insert ON waste_collection_records
        FOR INSERT WITH CHECK (client_generated_id IS NOT NULL AND EXISTS (
            SELECT 1 FROM waste_collection_points p
            WHERE p.id = collection_point_id AND p.event_id = waste_collection_records.event_id
              AND app_public_waste_point_access(p.id, waste_collection_records.event_id)
        ))
    """)


def downgrade() -> None:
    for name in (
        "waste_collection_records_public_insert",
        "waste_collection_records_public_read",
        "waste_collection_records_event_access",
    ):
        op.execute(f"DROP POLICY IF EXISTS {name} ON waste_collection_records")
    op.add_column("waste_records", sa.Column("collection_point_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("waste_records", sa.Column("submitter_name", sa.String(160), nullable=True))
    op.add_column("waste_records", sa.Column("submitter_rut", sa.String(20), nullable=True))
    op.add_column("waste_records", sa.Column("client_generated_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("waste_records", sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("waste_records", sa.Column("submission_source", sa.String(20), nullable=True))
    op.add_column("waste_records", sa.Column("synced_at", sa.DateTime(), nullable=True))
    op.execute("UPDATE waste_records SET submission_source='INTERNAL' WHERE submission_source IS NULL")
    op.alter_column("waste_records", "submission_source", server_default="INTERNAL", nullable=False)
    op.create_foreign_key("fk_waste_records_collection_point_id", "waste_records", "waste_collection_points", ["collection_point_id"], ["id"], ondelete="SET NULL")
    op.create_check_constraint("ck_waste_records_submission_source", "waste_records", "submission_source in ('INTERNAL', 'PUBLIC_FORM')")
    op.create_index("idx_waste_records_collection_point_id", "waste_records", ["collection_point_id"])
    op.create_unique_constraint("uq_waste_records_client_generated_id", "waste_records", ["client_generated_id"])
    op.execute("""
        INSERT INTO waste_records (
            id, event_id, waste_type_id, weight_kg, destination, collection_point_id,
            submitter_name, submitter_rut, client_generated_id, device_id,
            submission_source, recorded_at, synced_at, created_at
        )
        SELECT id, event_id, waste_type_id, weight_kg, 'OTHER', collection_point_id,
            submitter_name, submitter_rut, client_generated_id, device_id,
            'PUBLIC_FORM', recorded_at AT TIME ZONE 'UTC', synced_at AT TIME ZONE 'UTC', created_at
        FROM waste_collection_records
        ON CONFLICT (client_generated_id) DO NOTHING
    """)
    op.execute("ALTER TABLE waste_records ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY waste_records_public_waste_insert ON waste_records FOR INSERT WITH CHECK (
            submission_source = 'PUBLIC_FORM' AND client_generated_id IS NOT NULL
            AND EXISTS (SELECT 1 FROM waste_collection_points p
                WHERE p.id = collection_point_id AND app_public_waste_point_access(p.id, event_id))
        )
    """)
    op.execute("""
        CREATE POLICY waste_records_public_waste_read ON waste_records FOR SELECT USING (
            submission_source = 'PUBLIC_FORM' AND EXISTS (SELECT 1 FROM waste_collection_points p
                WHERE p.id = collection_point_id AND app_public_waste_point_access(p.id))
        )
    """)
    op.drop_table("waste_collection_records")
