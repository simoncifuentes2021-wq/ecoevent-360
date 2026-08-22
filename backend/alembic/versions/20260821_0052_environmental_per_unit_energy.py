"""Add explicit per-unit-hour environmental energy input.

Revision ID: 20260821_0052
Revises: 20260818_0051
"""

from alembic import op
import sqlalchemy as sa

revision = "20260821_0052"
down_revision = "20260818_0051"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "environmental_actions",
        sa.Column(
            "energy_input_mode",
            sa.String(30),
            nullable=False,
            server_default="TOTAL_MEASURED",
        ),
    )
    op.add_column(
        "environmental_actions",
        sa.Column("energy_per_unit_hour_kwh", sa.Numeric(16, 6)),
    )
    op.create_check_constraint(
        "ck_environmental_action_energy_input_mode",
        "environmental_actions",
        "energy_input_mode in ('TOTAL_MEASURED','PER_UNIT_HOUR')",
    )
    op.create_check_constraint(
        "ck_environmental_action_energy_per_unit_hour_positive",
        "environmental_actions",
        "energy_per_unit_hour_kwh is null or energy_per_unit_hour_kwh > 0",
    )
    op.create_check_constraint(
        "ck_environmental_action_per_unit_hour_complete",
        "environmental_actions",
        "energy_input_mode != 'PER_UNIT_HOUR' or (energy_per_unit_hour_kwh is not null and hours_used > 0)",
    )
    op.execute(
        """
        update environmental_methodologies
        set name = 'Torre diésel vs torre fotovoltaica',
            actual_technology = 'Torre fotovoltaica',
            description = 'Compara la energía equivalente que habría sido suministrada mediante una torre diésel con la energía de la solución fotovoltaica implementada. Calcula CO₂e evitado, diésel evitado y emisiones locales evitadas.'
        where id = '52000000-0000-4000-8000-000000000001'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        update environmental_methodologies
        set name = 'Torre diésel vs torre eléctrica (energía medida)',
            actual_technology = 'Torre conectada al SEN',
            description = 'Compara igual energía útil. Incluye CO2e y emisiones locales AP-42; requiere kWh medidos.'
        where id = '52000000-0000-4000-8000-000000000001'
        """
    )
    op.drop_constraint(
        "ck_environmental_action_per_unit_hour_complete", "environmental_actions"
    )
    op.drop_constraint(
        "ck_environmental_action_energy_per_unit_hour_positive", "environmental_actions"
    )
    op.drop_constraint("ck_environmental_action_energy_input_mode", "environmental_actions")
    op.drop_column("environmental_actions", "energy_per_unit_hour_kwh")
    op.drop_column("environmental_actions", "energy_input_mode")
