"""Add household electricity and intercity bus distance equivalences.

Revision ID: 20261119_0094
Revises: 20261118_0093
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20261119_0094"
down_revision: str | None = "20261118_0093"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    equivalences = sa.table(
        "eco_equivalence_factors",
        sa.column("id", postgresql.UUID(as_uuid=False)),
        sa.column("key", sa.String()),
        sa.column("name", sa.String()),
        sa.column("metric_source", sa.String()),
        sa.column("factor", sa.Numeric(20, 10)),
        sa.column("unit", sa.String()),
        sa.column("source", sa.Text()),
        sa.column("year", sa.Integer()),
        sa.column("is_active", sa.Boolean()),
    )
    op.bulk_insert(
        equivalences,
        [
            {
                "id": "53000000-0000-4000-8000-000000000003",
                "key": "HOUSEHOLD_ELECTRICITY_MONTHS",
                "name": "Meses de consumo eléctrico de una familia",
                "metric_source": "ENERGY_KWH",
                "factor": "0.0033333333",
                "unit": "meses de consumo familiar/kWh",
                "source": (
                    "Referencia de Greenway: consumo de 300 kWh al mes por familia. "
                    "Equivalencia comunicacional; el consumo real varía entre hogares."
                ),
                "year": 2026,
                "is_active": True,
            },
            {
                "id": "53000000-0000-4000-8000-000000000004",
                "key": "INTERCITY_BUS_KILOMETERS",
                "name": "Recorrido equivalente de bus interurbano",
                "metric_source": "FUEL_AVOIDED_L",
                "factor": "3.0000000000",
                "unit": "km de recorrido/L de diésel evitado",
                "source": (
                    "Referencia de Greenway: consumo promedio de 3 km/L y estanque de 600 L; "
                    "un estanque completo equivale a 1.800 km. La distancia calculada es "
                    "referencial y depende del bus, ruta, carga y condiciones de operación."
                ),
                "year": 2026,
                "is_active": True,
            },
        ],
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "delete from eco_equivalence_factors "
            "where key in ('HOUSEHOLD_ELECTRICITY_MONTHS', 'INTERCITY_BUS_KILOMETERS')"
        )
    )
