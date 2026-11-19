"""Add event-scoped field staff and per-activation recyclable materials.

Revision ID: 20261110_0090
Revises: 20261110_0089
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20261110_0090"
down_revision: str | None = "20261110_0089"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "recycling_activation_materials",
        sa.Column("activation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("recycling_activations.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("waste_type_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("waste_types.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    # Preserve today's behavior for existing activations until an administrator edits them.
    op.execute("""
        INSERT INTO recycling_activation_materials (activation_id, waste_type_id)
        SELECT a.id, w.id FROM recycling_activations a CROSS JOIN waste_types w
        WHERE w.is_recyclable IS TRUE
    """)

    op.create_table(
        "volunteer_field_staff",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("full_name", sa.String(180), nullable=False),
        sa.Column("rut", sa.String(16), nullable=False),
        sa.Column("rut_normalized", sa.String(12), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("event_id", "rut_normalized", name="uq_volunteer_field_staff_event_rut"),
    )
    op.create_index("idx_volunteer_field_staff_event_active", "volunteer_field_staff", ["event_id", "active"])
    op.create_table(
        "volunteer_field_staff_activations",
        sa.Column("field_staff_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("volunteer_field_staff.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("activation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("recycling_activations.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_volunteer_field_staff_activations_activation", "volunteer_field_staff_activations", ["activation_id"])
    op.add_column("material_contributions", sa.Column("registered_by_field_staff_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("volunteer_field_staff.id", ondelete="SET NULL")))
    op.create_index("idx_material_contributions_field_staff", "material_contributions", ["registered_by_field_staff_id", "registered_at"])

    op.execute("""
        CREATE OR REPLACE FUNCTION app_field_staff_can_access_event(event_uuid uuid)
        RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
          SELECT EXISTS (
            SELECT 1 FROM volunteer_field_staff s
            WHERE s.id = nullif(current_setting('app.field_staff_id', true), '')::uuid
              AND s.event_id = event_uuid AND s.active IS TRUE
          )
        $$
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION app_field_staff_can_access_activation(activation_uuid uuid)
        RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
          SELECT EXISTS (
            SELECT 1 FROM volunteer_field_staff_activations sa
            JOIN volunteer_field_staff s ON s.id = sa.field_staff_id
            WHERE s.id = nullif(current_setting('app.field_staff_id', true), '')::uuid
              AND sa.activation_id = activation_uuid AND s.active IS TRUE
          )
        $$
    """)

    for table in ("recycling_activation_materials", "volunteer_field_staff", "volunteer_field_staff_activations"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY volunteer_field_staff_access ON volunteer_field_staff FOR ALL
        USING (
          app_is_admin() OR app_can_view_event(event_id)
          OR id = nullif(current_setting('app.field_staff_id', true), '')::uuid
          OR (event_id = nullif(current_setting('app.field_staff_event_id', true), '')::uuid
              AND rut_normalized = nullif(current_setting('app.field_staff_rut', true), ''))
        )
        WITH CHECK (app_is_admin() OR app_can_view_event(event_id))
    """)
    op.execute("""
        CREATE POLICY volunteer_field_staff_activations_access ON volunteer_field_staff_activations FOR ALL
        USING (
          app_is_admin() OR app_can_view_event((SELECT event_id FROM recycling_activations WHERE id = activation_id))
          OR field_staff_id = nullif(current_setting('app.field_staff_id', true), '')::uuid
        )
        WITH CHECK (
          app_is_admin() OR app_can_view_event((SELECT event_id FROM recycling_activations WHERE id = activation_id))
        )
    """)
    op.execute("""
        CREATE POLICY recycling_activation_materials_access ON recycling_activation_materials FOR ALL
        USING (
          app_is_admin()
          OR app_can_view_event((SELECT event_id FROM recycling_activations WHERE id = activation_id))
          OR app_field_staff_can_access_activation(activation_id)
        )
        WITH CHECK (
          app_is_admin()
          OR app_can_view_event((SELECT event_id FROM recycling_activations WHERE id = activation_id))
        )
    """)

    op.execute("DROP POLICY IF EXISTS recycling_activations_access ON recycling_activations")
    op.execute("""
        CREATE POLICY recycling_activations_access ON recycling_activations FOR ALL
        USING (
          app_is_admin() OR app_can_view_event(event_id)
          OR (status='ACTIVE' AND public_slug=nullif(current_setting('app.public_volunteer_slug', true),''))
          OR app_volunteer_token_activation_access(id)
          OR app_field_staff_can_access_activation(id)
        )
        WITH CHECK (app_is_admin() OR app_can_view_event(event_id))
    """)
    op.execute("""
        CREATE POLICY recycling_activations_field_staff_event_read ON recycling_activations FOR SELECT
        USING (app_field_staff_can_access_event(event_id))
    """)

    op.execute("DROP POLICY IF EXISTS volunteers_select ON volunteers")
    op.execute("""
        CREATE POLICY volunteers_select ON volunteers FOR SELECT USING (
          app_is_admin()
          OR email_lookup_hash=nullif(current_setting('app.public_volunteer_email_hash',true),'')
          OR phone_normalized=nullif(current_setting('app.public_volunteer_phone',true),'')
          OR unique_code=nullif(current_setting('app.public_volunteer_code',true),'')
          OR app_volunteer_public_token_access(id)
          OR EXISTS (
            SELECT 1 FROM volunteer_activations va JOIN recycling_activations a ON a.id=va.activation_id
            WHERE va.volunteer_id=volunteers.id AND app_can_view_event(a.event_id)
          )
          OR EXISTS (
            SELECT 1 FROM volunteer_activations va JOIN recycling_activations a ON a.id=va.activation_id
            WHERE va.volunteer_id=volunteers.id AND app_field_staff_can_access_event(a.event_id)
          )
        )
    """)
    op.execute("DROP POLICY IF EXISTS volunteers_insert ON volunteers")
    op.execute("""
        CREATE POLICY volunteers_insert ON volunteers FOR INSERT WITH CHECK (
          app_is_admin()
          OR (email_lookup_hash=nullif(current_setting('app.public_volunteer_email_hash',true),'') AND consent_accepted)
          OR (consent_accepted AND app_field_staff_can_access_activation(
              nullif(current_setting('app.field_staff_activation_id',true),'')::uuid))
        )
    """)

    op.execute("DROP POLICY IF EXISTS volunteer_activations_access ON volunteer_activations")
    op.execute("""
        CREATE POLICY volunteer_activations_access ON volunteer_activations FOR ALL USING (
          app_is_admin()
          OR EXISTS (SELECT 1 FROM recycling_activations a WHERE a.id=activation_id AND app_can_view_event(a.event_id))
          OR (app_volunteer_public_activation_access(activation_id) AND app_volunteer_email_hash_matches(volunteer_id))
          OR app_volunteer_public_token_access(volunteer_id)
          OR app_field_staff_can_access_activation(activation_id)
        ) WITH CHECK (
          app_is_admin()
          OR EXISTS (SELECT 1 FROM recycling_activations a WHERE a.id=activation_id AND app_can_view_event(a.event_id))
          OR (app_volunteer_public_activation_access(activation_id) AND app_volunteer_email_hash_matches(volunteer_id))
          OR app_field_staff_can_access_activation(activation_id)
        )
    """)
    op.execute("""
        CREATE POLICY volunteer_activations_field_staff_event_read ON volunteer_activations FOR SELECT USING (
          EXISTS (SELECT 1 FROM recycling_activations a WHERE a.id=activation_id AND app_field_staff_can_access_event(a.event_id))
        )
    """)

    op.execute("DROP POLICY IF EXISTS material_contributions_access ON material_contributions")
    op.execute("""
        CREATE POLICY material_contributions_access ON material_contributions FOR ALL USING (
          app_is_admin()
          OR EXISTS (SELECT 1 FROM recycling_activations a WHERE a.id=activation_id AND app_can_view_event(a.event_id))
          OR app_volunteer_public_token_access(volunteer_id)
          OR EXISTS (SELECT 1 FROM recycling_activations a WHERE a.id=activation_id AND app_field_staff_can_access_event(a.event_id))
        ) WITH CHECK (
          app_is_admin()
          OR EXISTS (SELECT 1 FROM recycling_activations a WHERE a.id=activation_id AND app_can_view_event(a.event_id))
          OR app_field_staff_can_access_activation(activation_id)
        )
    """)
    op.execute("DROP POLICY IF EXISTS material_contribution_items_access ON material_contribution_items")
    op.execute("""
        CREATE POLICY material_contribution_items_access ON material_contribution_items FOR ALL USING (
          EXISTS (SELECT 1 FROM material_contributions c JOIN recycling_activations a ON a.id=c.activation_id
            WHERE c.id=contribution_id AND (
              app_is_admin() OR app_can_view_event(a.event_id) OR app_volunteer_public_token_access(c.volunteer_id)
              OR app_field_staff_can_access_event(a.event_id)
            ))
        ) WITH CHECK (
          EXISTS (SELECT 1 FROM material_contributions c JOIN recycling_activations a ON a.id=c.activation_id
            WHERE c.id=contribution_id AND (
              app_is_admin() OR app_can_view_event(a.event_id) OR app_field_staff_can_access_activation(a.id)
            ))
        )
    """)
    op.execute("""
        CREATE POLICY events_field_staff_read ON events FOR SELECT USING (app_field_staff_can_access_event(id))
    """)


def downgrade() -> None:
    for table, policy in (
        ("events", "events_field_staff_read"),
        ("material_contribution_items", "material_contribution_items_access"),
        ("material_contributions", "material_contributions_access"),
        ("volunteer_activations", "volunteer_activations_field_staff_event_read"),
        ("volunteer_activations", "volunteer_activations_access"),
        ("volunteers", "volunteers_insert"),
        ("volunteers", "volunteers_select"),
        ("recycling_activations", "recycling_activations_field_staff_event_read"),
        ("recycling_activations", "recycling_activations_access"),
        ("recycling_activation_materials", "recycling_activation_materials_access"),
        ("volunteer_field_staff_activations", "volunteer_field_staff_activations_access"),
        ("volunteer_field_staff", "volunteer_field_staff_access"),
    ):
        op.execute(f"DROP POLICY IF EXISTS {policy} ON {table}")
    for table in ("recycling_activation_materials", "volunteer_field_staff_activations", "volunteer_field_staff"):
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY recycling_activations_access ON recycling_activations FOR ALL USING (
          app_is_admin() OR app_can_view_event(event_id)
          OR (status='ACTIVE' AND public_slug=nullif(current_setting('app.public_volunteer_slug', true),''))
          OR app_volunteer_token_activation_access(id)
        ) WITH CHECK (app_is_admin() OR app_can_view_event(event_id))
    """)
    op.execute("""
        CREATE POLICY volunteers_select ON volunteers FOR SELECT USING (
          app_is_admin() OR email_lookup_hash=nullif(current_setting('app.public_volunteer_email_hash',true),'')
          OR phone_normalized=nullif(current_setting('app.public_volunteer_phone',true),'')
          OR unique_code=nullif(current_setting('app.public_volunteer_code',true),'')
          OR app_volunteer_public_token_access(id)
          OR EXISTS (SELECT 1 FROM volunteer_activations va JOIN recycling_activations a ON a.id=va.activation_id
            WHERE va.volunteer_id=volunteers.id AND app_can_view_event(a.event_id))
        )
    """)
    op.execute("""
        CREATE POLICY volunteers_insert ON volunteers FOR INSERT WITH CHECK (
          app_is_admin() OR (email_lookup_hash=nullif(current_setting('app.public_volunteer_email_hash',true),'') AND consent_accepted)
        )
    """)
    op.execute("""
        CREATE POLICY volunteer_activations_access ON volunteer_activations FOR ALL USING (
          app_is_admin() OR EXISTS (SELECT 1 FROM recycling_activations a WHERE a.id=activation_id AND app_can_view_event(a.event_id))
          OR (app_volunteer_public_activation_access(activation_id) AND app_volunteer_email_hash_matches(volunteer_id))
          OR app_volunteer_public_token_access(volunteer_id)
        ) WITH CHECK (
          app_is_admin() OR EXISTS (SELECT 1 FROM recycling_activations a WHERE a.id=activation_id AND app_can_view_event(a.event_id))
          OR (app_volunteer_public_activation_access(activation_id) AND app_volunteer_email_hash_matches(volunteer_id))
        )
    """)
    op.execute("""
        CREATE POLICY material_contributions_access ON material_contributions FOR ALL USING (
          app_is_admin() OR EXISTS (SELECT 1 FROM recycling_activations a WHERE a.id=activation_id AND app_can_view_event(a.event_id))
          OR app_volunteer_public_token_access(volunteer_id)
        ) WITH CHECK (
          app_is_admin() OR EXISTS (SELECT 1 FROM recycling_activations a WHERE a.id=activation_id AND app_can_view_event(a.event_id))
        )
    """)
    op.execute("""
        CREATE POLICY material_contribution_items_access ON material_contribution_items FOR ALL USING (
          EXISTS (SELECT 1 FROM material_contributions c WHERE c.id=contribution_id AND
            (app_is_admin() OR EXISTS (SELECT 1 FROM recycling_activations a WHERE a.id=c.activation_id AND app_can_view_event(a.event_id))
             OR app_volunteer_public_token_access(c.volunteer_id)))) WITH CHECK (
          EXISTS (SELECT 1 FROM material_contributions c JOIN recycling_activations a ON a.id=c.activation_id
            WHERE c.id=contribution_id AND (app_is_admin() OR app_can_view_event(a.event_id)))
        )
    """)
    op.execute("DROP POLICY IF EXISTS events_field_staff_read ON events")
    op.execute("DROP FUNCTION IF EXISTS app_field_staff_can_access_activation(uuid)")
    op.execute("DROP FUNCTION IF EXISTS app_field_staff_can_access_event(uuid)")
    op.drop_index("idx_material_contributions_field_staff", table_name="material_contributions")
    op.drop_column("material_contributions", "registered_by_field_staff_id")
    op.drop_index("idx_volunteer_field_staff_activations_activation", table_name="volunteer_field_staff_activations")
    op.drop_table("volunteer_field_staff_activations")
    op.drop_index("idx_volunteer_field_staff_event_active", table_name="volunteer_field_staff")
    op.drop_table("volunteer_field_staff")
    op.drop_table("recycling_activation_materials")
