"""Add traceable environmental impact module.

Revision ID: 20260818_0049
Revises: 20260816_0048
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260818_0049"
down_revision = "20260816_0048"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)


def timestamps():
    return [
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "environmental_factors",
        sa.Column("id", UUID, server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("impact_type", sa.String(30), nullable=False),
        sa.Column("technology", sa.String(120), nullable=False),
        sa.Column("pollutant", sa.String(30)),
        sa.Column("unit_basis", sa.String(50), nullable=False),
        sa.Column("factor_value", sa.Numeric(20, 10), nullable=False),
        sa.Column("factor_unit", sa.String(80), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text()),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("country", sa.String(100)),
        sa.Column("methodology", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("TRUE"), nullable=False),
        *timestamps(),
        sa.CheckConstraint("factor_value >= 0", name="ck_environmental_factor_nonnegative"),
    )
    op.create_index(
        "idx_environmental_factors_lookup",
        "environmental_factors",
        ["impact_type", "technology", "unit_basis", "is_active"],
    )
    op.create_table(
        "environmental_methodologies",
        sa.Column("id", UUID, server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("action_type", sa.String(40), nullable=False),
        sa.Column("baseline_technology", sa.String(180), nullable=False),
        sa.Column("actual_technology", sa.String(180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "parameters", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("TRUE"), nullable=False),
        *timestamps(),
        sa.CheckConstraint(
            "action_type in ('ELECTRIC_LIGHTING_TOWER','ELECTRIC_MOTORCYCLE','ELECTRIC_CART','SOLAR_ENERGY','ELECTRIC_VEHICLE','BIKE_MOBILITY','PUBLIC_TRANSPORT','OTHER')",
            name="ck_environmental_methodology_action_type",
        ),
    )
    op.create_index(
        "idx_environmental_methodologies_type_active",
        "environmental_methodologies",
        ["action_type", "is_active"],
    )
    op.create_table(
        "eco_equivalence_factors",
        sa.Column("id", UUID, server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("key", sa.String(80), nullable=False),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("metric_source", sa.String(40), nullable=False),
        sa.Column("factor", sa.Numeric(20, 10), nullable=False),
        sa.Column("unit", sa.String(80), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("TRUE"), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("key", name="uq_eco_equivalence_factors_key"),
        sa.CheckConstraint("factor >= 0", name="ck_eco_equivalence_factor_nonnegative"),
    )
    op.create_table(
        "environmental_actions",
        sa.Column("id", UUID, server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("event_id", UUID, sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", UUID),
        sa.Column(
            "methodology_id",
            UUID,
            sa.ForeignKey("environmental_methodologies.id", ondelete="RESTRICT"),
        ),
        sa.Column("action_type", sa.String(40), nullable=False),
        sa.Column("status", sa.String(30), server_default="INCOMPLETE", nullable=False),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("quantity_used", sa.Numeric(14, 4), nullable=False),
        sa.Column("hours_used", sa.Numeric(14, 4)),
        sa.Column("distance_km", sa.Numeric(16, 4)),
        sa.Column("energy_kwh", sa.Numeric(16, 6)),
        sa.Column("power_kw", sa.Numeric(16, 6)),
        sa.Column("energy_source", sa.String(20)),
        sa.Column("notes", sa.Text()),
        sa.Column("created_by", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        *timestamps(),
        sa.ForeignKeyConstraint(
            ["event_id", "session_id"],
            ["event_sessions.event_id", "event_sessions.id"],
            name="fk_environmental_action_event_session",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint("quantity_used > 0", name="ck_environmental_action_quantity_positive"),
        sa.CheckConstraint(
            "hours_used is null or hours_used >= 0",
            name="ck_environmental_action_hours_nonnegative",
        ),
        sa.CheckConstraint(
            "distance_km is null or distance_km >= 0",
            name="ck_environmental_action_distance_nonnegative",
        ),
        sa.CheckConstraint(
            "energy_kwh is null or energy_kwh >= 0",
            name="ck_environmental_action_energy_nonnegative",
        ),
        sa.CheckConstraint(
            "power_kw is null or power_kw >= 0", name="ck_environmental_action_power_nonnegative"
        ),
    )
    for name, columns in (
        ("idx_environmental_actions_event_id", ["event_id"]),
        ("idx_environmental_actions_session_id", ["session_id"]),
        ("idx_environmental_actions_methodology_id", ["methodology_id"]),
    ):
        op.create_index(name, "environmental_actions", columns)
    op.create_table(
        "environmental_action_metrics",
        sa.Column("id", UUID, server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column(
            "action_id",
            UUID,
            sa.ForeignKey("environmental_actions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("metric_key", sa.String(40), nullable=False),
        sa.Column("unit", sa.String(40), nullable=False),
        sa.Column("calculated_value", sa.Numeric(20, 8)),
        sa.Column("reported_value", sa.Numeric(20, 8)),
        sa.Column(
            "is_manual_override", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False
        ),
        sa.Column("override_reason", sa.Text()),
        sa.Column("calculation_method", sa.Text(), nullable=False),
        sa.Column("calculation_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("calculated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.UniqueConstraint("action_id", "metric_key", name="uq_environmental_action_metric_key"),
        sa.CheckConstraint(
            "reported_value is null or override_reason is not null",
            name="ck_environmental_metric_override_reason",
        ),
    )
    op.create_index(
        "idx_environmental_action_metrics_action_id", "environmental_action_metrics", ["action_id"]
    )

    for table in (
        "environmental_factors",
        "environmental_methodologies",
        "eco_equivalence_factors",
        "environmental_actions",
        "environmental_action_metrics",
    ):
        op.execute(f"alter table {table} enable row level security")
        op.execute(f"alter table {table} force row level security")
    op.execute(
        "create policy environmental_actions_select on environmental_actions for select using (app_can_view_event(event_id))"
    )
    op.execute(
        "create policy environmental_actions_write on environmental_actions for all using ((app_is_admin() or app_current_role() = 'SUPERVISOR') and app_can_view_event(event_id)) with check ((app_is_admin() or app_current_role() = 'SUPERVISOR') and app_can_view_event(event_id))"
    )
    op.execute(
        "create policy environmental_action_metrics_select on environmental_action_metrics for select using (exists (select 1 from environmental_actions a where a.id = action_id and app_can_view_event(a.event_id)))"
    )
    op.execute(
        "create policy environmental_action_metrics_write on environmental_action_metrics for all using (exists (select 1 from environmental_actions a where a.id = action_id and (app_is_admin() or app_current_role() = 'SUPERVISOR') and app_can_view_event(a.event_id))) with check (exists (select 1 from environmental_actions a where a.id = action_id and (app_is_admin() or app_current_role() = 'SUPERVISOR') and app_can_view_event(a.event_id)))"
    )
    for table in (
        "environmental_factors",
        "environmental_methodologies",
        "eco_equivalence_factors",
    ):
        op.execute(
            f"create policy {table}_select on {table} for select using (app_current_role() in ('SUPER_ADMIN','ADMIN','SUPERVISOR'))"
        )
        op.execute(
            f"create policy {table}_write on {table} for all using (app_is_admin()) with check (app_is_admin())"
        )


def downgrade() -> None:
    for table in (
        "environmental_action_metrics",
        "environmental_actions",
        "eco_equivalence_factors",
        "environmental_methodologies",
        "environmental_factors",
    ):
        op.drop_table(table)
