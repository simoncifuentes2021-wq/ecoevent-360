"""Add volunteer activations and recycling contribution tracking.

Revision ID: 20261110_0088
Revises: 20261101_0087
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20261110_0088"
down_revision: str | None = "20261101_0087"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "volunteers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("full_name", sa.String(180), nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("email_normalized", sa.String(254), nullable=False),
        sa.Column("email_lookup_hash", sa.String(64), nullable=False),
        sa.Column("phone", sa.String(40)),
        sa.Column("phone_normalized", sa.String(32)),
        sa.Column("organization", sa.String(180)),
        sa.Column("unique_code", sa.String(24), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="ACTIVE"),
        sa.Column("consent_accepted", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("consent_accepted_at", sa.DateTime(timezone=True)),
        sa.Column("consent_version", sa.String(32)),
        sa.Column("marketing_consent", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint("consent_accepted or consent_accepted_at is null", name="ck_volunteers_consent_timestamp"),
        sa.CheckConstraint("status in ('ACTIVE','INACTIVE','ARCHIVED')", name="ck_volunteers_status"),
        sa.UniqueConstraint("email_normalized", name="uq_volunteers_email_normalized"),
        sa.UniqueConstraint("unique_code", name="uq_volunteers_unique_code"),
    )
    op.create_index("idx_volunteers_email_hash", "volunteers", ["email_lookup_hash"])
    op.create_index("idx_volunteers_phone_normalized", "volunteers", ["phone_normalized"])
    op.create_index("idx_volunteers_status", "volunteers", ["status"])

    op.create_table(
        "recycling_activations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("events.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("event_sessions.id", ondelete="SET NULL")),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("location_name", sa.String(180)),
        sa.Column("address", sa.Text()),
        sa.Column("latitude", sa.Numeric(10, 7)),
        sa.Column("longitude", sa.Numeric(10, 7)),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True)),
        sa.Column("responsible_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("status", sa.String(16), nullable=False, server_default="DRAFT"),
        sa.Column("capacity", sa.Integer()),
        sa.Column("public_slug", sa.String(72), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint("status in ('DRAFT','ACTIVE','CLOSED','CANCELLED','ARCHIVED')", name="ck_recycling_activations_status"),
        sa.CheckConstraint("ends_at is null or ends_at >= starts_at", name="ck_recycling_activations_dates"),
        sa.CheckConstraint("capacity is null or capacity > 0", name="ck_recycling_activations_capacity"),
        sa.UniqueConstraint("public_slug", name="uq_recycling_activations_public_slug"),
    )
    op.create_index("idx_recycling_activations_event", "recycling_activations", ["event_id", "status", "starts_at"])

    op.create_table(
        "volunteer_activations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("volunteer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("volunteers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("activation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("recycling_activations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("check_in_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(16), nullable=False, server_default="REGISTERED"),
        sa.Column("notes", sa.Text()),
        sa.CheckConstraint("status in ('REGISTERED','CHECKED_IN','CANCELLED')", name="ck_volunteer_activations_status"),
        sa.UniqueConstraint("volunteer_id", "activation_id", name="uq_volunteer_activation_person"),
    )
    op.create_index("idx_volunteer_activations_activation", "volunteer_activations", ["activation_id", "status"])
    op.create_index("idx_volunteer_activations_volunteer", "volunteer_activations", ["volunteer_id", "registered_at"])

    op.create_table(
        "recyclable_materials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("name_normalized", sa.String(100), nullable=False),
        sa.Column("category", sa.String(100)),
        sa.Column("unit", sa.String(8), nullable=False, server_default="kg"),
        sa.Column("description", sa.Text()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint("unit in ('kg')", name="ck_recyclable_materials_unit"),
        sa.UniqueConstraint("name_normalized", name="uq_recyclable_materials_name_normalized"),
    )
    op.create_index("idx_recyclable_materials_active_order", "recyclable_materials", ["active", "sort_order"])
    op.execute("""
        INSERT INTO recyclable_materials (name, name_normalized, category, sort_order)
        VALUES ('PET','pet','Plásticos',10),('Vidrio','vidrio','Vidrio',20),
               ('Cartón','cartón','Papel y cartón',30),('Papel','papel','Papel y cartón',40),
               ('Latas de aluminio','latas de aluminio','Metales',50),('Metales','metales','Metales',60),
               ('Tetra Pak','tetra pak','Envases',70),('Electrónicos','electrónicos','Electrónicos',80),
               ('Otro','otro','Otros',90)
    """)

    op.create_table(
        "material_contributions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("volunteer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("volunteers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("activation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("recycling_activations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("registered_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("updated_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("notes", sa.Text()),
        sa.Column("total_weight_kg", sa.Numeric(12, 3), nullable=False, server_default="0"),
        sa.Column("status", sa.String(12), nullable=False, server_default="ACTIVE"),
        sa.Column("void_reason", sa.Text()),
        sa.Column("voided_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("voided_at", sa.DateTime(timezone=True)),
        sa.Column("idempotency_key", sa.String(80)),
        sa.Column("email_status", sa.String(12), nullable=False, server_default="PENDING"),
        sa.Column("email_sent_at", sa.DateTime(timezone=True)),
        sa.Column("email_error", sa.String(240)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint("status in ('ACTIVE','VOID')", name="ck_material_contributions_status"),
        sa.CheckConstraint("email_status in ('PENDING','SENT','FAILED','SKIPPED')", name="ck_material_contributions_email_status"),
        sa.CheckConstraint("total_weight_kg >= 0", name="ck_material_contributions_total_nonnegative"),
        sa.UniqueConstraint("activation_id", "idempotency_key", name="uq_material_contributions_idempotency"),
    )
    op.create_index("idx_material_contributions_activation_date", "material_contributions", ["activation_id", "registered_at"])
    op.create_index("idx_material_contributions_volunteer_date", "material_contributions", ["volunteer_id", "registered_at"])
    op.create_index("idx_material_contributions_status", "material_contributions", ["status"])

    op.create_table(
        "material_contribution_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("contribution_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("material_contributions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("material_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("recyclable_materials.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("material_name_snapshot", sa.String(100), nullable=False),
        sa.Column("unit_snapshot", sa.String(8), nullable=False, server_default="kg"),
        sa.Column("weight_kg", sa.Numeric(12, 3), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint("weight_kg > 0 and weight_kg <= 1000000", name="ck_material_contribution_items_weight_positive"),
        sa.UniqueConstraint("contribution_id", "material_id", name="uq_material_contribution_material"),
    )
    op.create_index("idx_material_contribution_items_material", "material_contribution_items", ["material_id", "contribution_id"])

    op.create_table(
        "volunteer_access_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("volunteer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("volunteers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("token_hash", name="uq_volunteer_access_tokens_hash"),
    )
    op.create_index("idx_volunteer_access_tokens_volunteer_expiry", "volunteer_access_tokens", ["volunteer_id", "expires_at"])

    op.add_column("evidences", sa.Column("volunteer_contribution_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("material_contributions.id", ondelete="SET NULL")))
    op.create_index("idx_evidences_volunteer_contribution", "evidences", ["volunteer_contribution_id"])

    # Narrow, capability-based policies for public registration and private history.
    op.execute("""
        CREATE OR REPLACE FUNCTION app_volunteer_public_activation_access(activation_uuid uuid)
        RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
          SELECT EXISTS (SELECT 1 FROM recycling_activations a
            WHERE a.id=activation_uuid AND a.status='ACTIVE'
              AND a.public_slug=nullif(current_setting('app.public_volunteer_slug', true),''))
        $$
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION app_volunteer_public_token_access(volunteer_uuid uuid)
        RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
          SELECT EXISTS (SELECT 1 FROM volunteer_access_tokens t
            WHERE t.volunteer_id=volunteer_uuid AND t.revoked_at IS NULL AND t.expires_at>now()
              AND t.token_hash=nullif(current_setting('app.public_volunteer_token_hash', true),''))
        $$
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION app_volunteer_email_hash_matches(volunteer_uuid uuid)
        RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
          SELECT EXISTS (SELECT 1 FROM volunteers v WHERE v.id=volunteer_uuid
            AND v.email_lookup_hash=nullif(current_setting('app.public_volunteer_email_hash',true),''))
        $$
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION app_volunteer_event_public_access(event_uuid uuid)
        RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
          SELECT EXISTS (SELECT 1 FROM recycling_activations a WHERE a.event_id=event_uuid
            AND a.status='ACTIVE' AND a.public_slug=nullif(current_setting('app.public_volunteer_slug', true),''))
        $$
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION app_volunteer_token_activation_access(activation_uuid uuid)
        RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
          SELECT EXISTS (SELECT 1 FROM material_contributions c JOIN recycling_activations a ON a.id=c.activation_id
            WHERE c.activation_id=activation_uuid AND c.status='ACTIVE'
              AND a.status <> 'ARCHIVED' AND app_volunteer_public_token_access(c.volunteer_id))
        $$
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION app_volunteer_token_event_access(event_uuid uuid)
        RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
          SELECT EXISTS (SELECT 1 FROM material_contributions c JOIN recycling_activations a ON a.id=c.activation_id
            WHERE a.event_id=event_uuid AND c.status='ACTIVE'
              AND app_volunteer_public_token_access(c.volunteer_id))
        $$
    """)

    for table in (
        "volunteers", "recycling_activations", "volunteer_activations",
        "recyclable_materials", "material_contributions", "material_contribution_items",
        "volunteer_access_tokens",
    ):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY volunteers_select ON volunteers FOR SELECT USING (
          app_is_admin()
          OR email_lookup_hash=nullif(current_setting('app.public_volunteer_email_hash',true),'')
          OR phone_normalized=nullif(current_setting('app.public_volunteer_phone',true),'')
          OR unique_code=nullif(current_setting('app.public_volunteer_code',true),'')
          OR app_volunteer_public_token_access(id)
          OR EXISTS (SELECT 1 FROM volunteer_activations va JOIN recycling_activations a ON a.id=va.activation_id
            WHERE va.volunteer_id=volunteers.id AND app_can_view_event(a.event_id)))
    """)
    op.execute("""
        CREATE POLICY volunteers_insert ON volunteers FOR INSERT WITH CHECK (
          app_is_admin() OR (email_lookup_hash=nullif(current_setting('app.public_volunteer_email_hash',true),'') AND consent_accepted))
    """)
    op.execute("""
        CREATE POLICY volunteers_update ON volunteers FOR UPDATE USING (
          app_is_admin() OR email_lookup_hash=nullif(current_setting('app.public_volunteer_email_hash',true),'')
          OR app_volunteer_public_token_access(id)) WITH CHECK (
          app_is_admin() OR email_lookup_hash=nullif(current_setting('app.public_volunteer_email_hash',true),'')
          OR app_volunteer_public_token_access(id))
    """)

    op.execute("""
        CREATE POLICY recycling_activations_access ON recycling_activations FOR ALL USING (
          app_is_admin() OR app_can_view_event(event_id) OR
          (status='ACTIVE' AND public_slug=nullif(current_setting('app.public_volunteer_slug',true),''))
          OR app_volunteer_token_activation_access(id))
        WITH CHECK (app_is_admin() OR app_can_view_event(event_id))
    """)
    op.execute("""
        CREATE POLICY volunteer_activations_access ON volunteer_activations FOR ALL USING (
          app_is_admin() OR EXISTS (SELECT 1 FROM recycling_activations a WHERE a.id=activation_id AND app_can_view_event(a.event_id))
          OR (app_volunteer_public_activation_access(activation_id) AND
              app_volunteer_email_hash_matches(volunteer_id))
          OR app_volunteer_public_token_access(volunteer_id)) WITH CHECK (
          app_is_admin() OR EXISTS (SELECT 1 FROM recycling_activations a WHERE a.id=activation_id AND app_can_view_event(a.event_id))
          OR (app_volunteer_public_activation_access(activation_id) AND
              app_volunteer_email_hash_matches(volunteer_id)))
    """)
    op.execute("CREATE POLICY recyclable_materials_read ON recyclable_materials FOR SELECT USING (true)")
    op.execute("CREATE POLICY recyclable_materials_admin_write ON recyclable_materials FOR ALL USING (app_is_admin()) WITH CHECK (app_is_admin())")
    op.execute("""
        CREATE POLICY material_contributions_access ON material_contributions FOR ALL USING (
          app_is_admin() OR EXISTS (SELECT 1 FROM recycling_activations a WHERE a.id=activation_id AND app_can_view_event(a.event_id))
          OR app_volunteer_public_token_access(volunteer_id)) WITH CHECK (
          app_is_admin() OR EXISTS (SELECT 1 FROM recycling_activations a WHERE a.id=activation_id AND app_can_view_event(a.event_id)))
    """)
    op.execute("""
        CREATE POLICY material_contribution_items_access ON material_contribution_items FOR ALL USING (
          EXISTS (SELECT 1 FROM material_contributions c WHERE c.id=contribution_id AND
            (app_is_admin() OR EXISTS (SELECT 1 FROM recycling_activations a WHERE a.id=c.activation_id AND app_can_view_event(a.event_id))
             OR app_volunteer_public_token_access(c.volunteer_id)))) WITH CHECK (
          EXISTS (SELECT 1 FROM material_contributions c JOIN recycling_activations a ON a.id=c.activation_id
            WHERE c.id=contribution_id AND (app_is_admin() OR app_can_view_event(a.event_id))))
    """)
    op.execute("""
        CREATE POLICY volunteer_access_tokens_access ON volunteer_access_tokens FOR ALL USING (
          app_is_admin() OR token_hash=nullif(current_setting('app.public_volunteer_token_hash',true),'')
          OR app_volunteer_email_hash_matches(volunteer_id))
        WITH CHECK (app_is_admin() OR app_volunteer_email_hash_matches(volunteer_id))
    """)
    # Make only the event name needed by the public activation page visible through its active slug.
    op.execute("""
        CREATE POLICY events_public_volunteer_activation_read ON events FOR SELECT USING (
          app_volunteer_event_public_access(id) OR app_volunteer_token_event_access(id))
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS events_public_volunteer_activation_read ON events")
    for table, policy in (
        ("volunteer_access_tokens", "volunteer_access_tokens_access"),
        ("material_contribution_items", "material_contribution_items_access"),
        ("material_contributions", "material_contributions_access"),
        ("recyclable_materials", "recyclable_materials_admin_write"),
        ("recyclable_materials", "recyclable_materials_read"),
        ("volunteer_activations", "volunteer_activations_access"),
        ("recycling_activations", "recycling_activations_access"),
        ("volunteers", "volunteers_update"),
        ("volunteers", "volunteers_insert"),
        ("volunteers", "volunteers_select"),
    ):
        op.execute(f"DROP POLICY IF EXISTS {policy} ON {table}")
    for table in (
        "volunteer_access_tokens", "material_contribution_items", "material_contributions",
        "recyclable_materials", "volunteer_activations", "recycling_activations", "volunteers",
    ):
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    op.execute("DROP FUNCTION IF EXISTS app_volunteer_event_public_access(uuid)")
    op.execute("DROP FUNCTION IF EXISTS app_volunteer_token_event_access(uuid)")
    op.execute("DROP FUNCTION IF EXISTS app_volunteer_token_activation_access(uuid)")
    op.execute("DROP FUNCTION IF EXISTS app_volunteer_email_hash_matches(uuid)")
    op.execute("DROP FUNCTION IF EXISTS app_volunteer_public_token_access(uuid)")
    op.execute("DROP FUNCTION IF EXISTS app_volunteer_public_activation_access(uuid)")
    op.drop_index("idx_evidences_volunteer_contribution", table_name="evidences")
    op.drop_column("evidences", "volunteer_contribution_id")
    op.drop_table("volunteer_access_tokens")
    op.drop_index("idx_material_contribution_items_material", table_name="material_contribution_items")
    op.drop_table("material_contribution_items")
    op.drop_index("idx_material_contributions_status", table_name="material_contributions")
    op.drop_index("idx_material_contributions_volunteer_date", table_name="material_contributions")
    op.drop_index("idx_material_contributions_activation_date", table_name="material_contributions")
    op.drop_table("material_contributions")
    op.drop_index("idx_recyclable_materials_active_order", table_name="recyclable_materials")
    op.drop_table("recyclable_materials")
    op.drop_index("idx_volunteer_activations_volunteer", table_name="volunteer_activations")
    op.drop_index("idx_volunteer_activations_activation", table_name="volunteer_activations")
    op.drop_table("volunteer_activations")
    op.drop_index("idx_recycling_activations_event", table_name="recycling_activations")
    op.drop_table("recycling_activations")
    op.drop_index("idx_volunteers_status", table_name="volunteers")
    op.drop_index("idx_volunteers_phone_normalized", table_name="volunteers")
    op.drop_index("idx_volunteers_email_hash", table_name="volunteers")
    op.drop_table("volunteers")
