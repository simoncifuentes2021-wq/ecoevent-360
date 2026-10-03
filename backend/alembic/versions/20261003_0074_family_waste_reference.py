"""Set the family waste equivalence to the agreed 4.5 kg daily reference.

Revision ID: 20261003_0074
Revises: 20261003_0073
"""

from alembic import op
import sqlalchemy as sa

revision = "20261003_0074"
down_revision = "20261003_0073"
branch_labels = None
depends_on = None

FAMILY_KEY = "FAMILY_DAILY_WASTE"
SOURCE = (
    "Santiago Recicla / MMA, Hoja de Ruta de Economía Circular RM, dato SUBDERE 2024: "
    "1.12 kg por persona al día. Referencia redondeada para una familia de 4 personas: "
    "4.5 kg/día, 135 kg en 30 días y 1,642.5 kg en 365 días."
)
SOURCE_URL = "https://santiagorecicla.mma.gob.cl/wp-content/uploads/2024/08/Hoja-de-Ruta-EC-RM-19ago.pdf"


def upgrade() -> None:
    bind = op.get_bind()
    family = bind.execute(
        sa.text(
            "select id from waste_collection_equivalence_factors "
            "where kind = 'FAMILY_DAYS' "
            "order by (key = :key) desc, is_active desc, created_at asc limit 1"
        ),
        {"key": FAMILY_KEY},
    ).first()

    if family:
        bind.execute(
            sa.text(
                "update waste_collection_equivalence_factors "
                "set key = :key, name = :name, reference_kg = 4.5, "
                "display_unit = :unit, source = :source, source_url = :source_url, "
                "year = 2024, is_active = true, updated_at = now() where id = :id"
            ),
            {
                "key": FAMILY_KEY,
                "name": "Residuos de una familia de 4 personas",
                "unit": "días de residuos de una familia",
                "source": SOURCE,
                "source_url": SOURCE_URL,
                "id": family.id,
            },
        )
        bind.execute(
            sa.text(
                "update waste_collection_equivalence_factors set is_active = false, updated_at = now() "
                "where kind = 'FAMILY_DAYS' and id <> :id"
            ),
            {"id": family.id},
        )
        return

    bind.execute(
        sa.text(
            "insert into waste_collection_equivalence_factors "
            "(id, key, kind, waste_type_id, name, reference_kg, display_unit, source, source_url, year, is_active, created_at, updated_at) "
            "values (uuid_generate_v4(), :key, 'FAMILY_DAYS', null, :name, 4.5, :unit, :source, :source_url, 2024, true, now(), now())"
        ),
        {
            "key": FAMILY_KEY,
            "name": "Residuos de una familia de 4 personas",
            "unit": "días de residuos de una familia",
            "source": SOURCE,
            "source_url": SOURCE_URL,
        },
    )


def downgrade() -> None:
    # Preserve the configured family factor and any later administrative edits.
    pass
