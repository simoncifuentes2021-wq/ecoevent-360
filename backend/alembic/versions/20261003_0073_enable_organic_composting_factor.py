"""Enable the organic composting comparison now that the route is confirmed.

Revision ID: 20261003_0073
Revises: 20261002_0072
"""

from alembic import op
import sqlalchemy as sa

revision = "20261003_0073"
down_revision = "20261002_0072"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "update waste_collection_equivalence_factors "
            "set is_active = true, "
            "source = :source, "
            "source_url = :source_url, "
            "updated_at = now() "
            "where key like '%FOOD_WASTE_CO2E' "
            "and waste_type_id = (select id from waste_types where name = :type_name)"
        ).bindparams(
            source=(
                "EPA WARM v16: diferencia estimada entre compostaje y relleno sanitario para residuos alimentarios. "
                "La ruta a compostaje de los residuos orgánicos del evento fue confirmada por el usuario; "
                "la estimación requiere que el flujo corresponda a residuos alimentarios. Referencia de EE.UU."
            ),
            source_url="https://www.epa.gov/system/files/documents/2023-12/warm_organic_materials_v16_dec.pdf",
            type_name="Residuos Orgánicos",
        )
    )


def downgrade() -> None:
    # Keep the administrator's active setting if the migration is rolled back.
    pass
