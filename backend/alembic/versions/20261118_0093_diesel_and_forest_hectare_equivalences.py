"""Update environmental communication equivalences to diesel and hectares.

Revision ID: 20261118_0093
Revises: 20261111_0092
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20261118_0093"
down_revision: str | None = "20261111_0092"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    equivalences = sa.table(
        "eco_equivalence_factors",
        sa.column("key", sa.String()),
        sa.column("name", sa.String()),
        sa.column("factor", sa.Numeric(20, 10)),
        sa.column("unit", sa.String()),
        sa.column("source", sa.Text()),
        sa.column("year", sa.Integer()),
    )

    # 10.21 kg CO2 per US gallon of diesel / 3.785411784 L per US gallon.
    diesel_liters_per_kg = 3.785411784 / 10.21
    # The seeded forest factor is 0.001 acre-year/kg CO2e; convert acres to ha.
    hectares_per_kg = 0.001 * 0.40468564224

    op.execute(
        equivalences.update()
        .where(equivalences.c.key == "GASOLINE_LITERS")
        .values(
            key="DIESEL_LITERS",
            name="Litros de diésel no consumidos",
            factor=sa.literal(diesel_liters_per_kg),
            unit="L/kgCO2e",
            source=(
                "US EPA, GHG Emission Factors Hub 2025: 10,21 kg CO2/galón US de diésel; "
                "convertido con 3,785411784 L/galón US. Equivalencia comunicacional, "
                "no medición directa de combustible."
            ),
            year=2025,
        )
    )
    op.execute(
        equivalences.update()
        .where(equivalences.c.key == "FOREST_ACRE_YEAR")
        .values(
            key="FOREST_HECTARE_YEAR",
            name="Hectáreas de bosque capturando CO2 durante un año",
            factor=sa.literal(hectares_per_kg),
            unit="ha-año/kgCO2e",
            source=(
                "US EPA Greenhouse Gas Equivalencies Calculator: 1,00 t CO2/acre-año; "
                "convertido con 1 acre = 0,40468564224 ha y 1 t = 1.000 kg. "
                "Estimación contextual para bosque promedio de EE. UU.; "
                "no representa compensación ni un bosque local específico."
            ),
            year=2024,
        )
    )


def downgrade() -> None:
    equivalences = sa.table(
        "eco_equivalence_factors",
        sa.column("key", sa.String()),
        sa.column("name", sa.String()),
        sa.column("factor", sa.Numeric(20, 10)),
        sa.column("unit", sa.String()),
        sa.column("source", sa.Text()),
        sa.column("year", sa.Integer()),
    )
    op.execute(
        equivalences.update()
        .where(equivalences.c.key == "DIESEL_LITERS")
        .values(
            key="GASOLINE_LITERS",
            name="Litros de gasolina no consumidos",
            factor=sa.literal(0.4251437),
            unit="L/kgCO2e",
            source="US EPA: 8,887 kgCO2 por galón de gasolina; convertido a litros",
            year=2024,
        )
    )
    op.execute(
        equivalences.update()
        .where(equivalences.c.key == "FOREST_HECTARE_YEAR")
        .values(
            key="FOREST_ACRE_YEAR",
            name="Acres de bosque estadounidense capturando CO2 durante un año",
            factor=sa.literal(0.001),
            unit="acre-año/kgCO2e",
            source=(
                "US EPA: 1,00 tonelada CO2 por acre-año; equivalencia contextual, "
                "no compensación"
            ),
            year=2024,
        )
    )
