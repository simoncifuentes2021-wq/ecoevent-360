"""Keep recommended factors on canonical materials and seed Tetra Pak content.

Revision ID: 20261002_0071
Revises: 20261002_0070
"""

from __future__ import annotations

import re
import unicodedata

from alembic import op
import sqlalchemy as sa

revision = "20261002_0071"
down_revision = "20261002_0070"
branch_labels = None
depends_on = None

TETRA_PAK_URL = "https://www.tetrapak.com/sustainability/planet/packaging-material"


def _plain(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    return re.sub(r"[^a-z0-9]+", " ", "".join(char for char in value if not unicodedata.combining(char))).strip()


def upgrade() -> None:
    bind = op.get_bind()
    materials = bind.execute(sa.text("select id, name from waste_types")).all()

    # These rows were created by 0070 from broad legacy-name matches; remove
    # only the generated recommendations from non-canonical duplicate types.
    wrong_ids = [row.id for row in materials if _plain(row.name) in {"aluminio", "organico qa 20260528194347"}]
    if wrong_ids:
        bind.execute(
            sa.text(
                "delete from waste_collection_equivalence_factors "
                "where waste_type_id = any(:ids) and kind = 'MATERIAL_UNITS' "
                "and (key like '%_ALUMINUM_KWH' or key like '%_FOOD_WASTE_CO2E')"
            ),
            {"ids": wrong_ids},
        )

    tetra = next((row for row in materials if _plain(row.name) in {"tetrapack", "tetrapak", "tetra pak", "envase larga vida"}), None)
    if tetra is None:
        return

    items = [
        ("TETRA_FIBER", "Fibra de cartón contenida en envases asépticos", 1 / 0.70, "kg de fibra de cartón estimados"),
        ("TETRA_POLYMERS", "Polímeros contenidos en envases asépticos", 1 / 0.25, "kg de polímeros estimados"),
        ("TETRA_ALUMINUM", "Aluminio contenido en envases asépticos", 1 / 0.05, "kg de aluminio estimados"),
    ]
    for suffix, name, reference_kg, unit in items:
        key = f"MATERIAL_{tetra.id.hex.upper()}_{suffix}"
        if bind.scalar(sa.text("select 1 from waste_collection_equivalence_factors where key = :key"), {"key": key}):
            continue
        bind.execute(
            sa.text(
                "insert into waste_collection_equivalence_factors "
                "(id, key, kind, waste_type_id, name, reference_kg, display_unit, source, source_url, year, is_active, created_at, updated_at) "
                "values (uuid_generate_v4(), :key, 'MATERIAL_UNITS', :waste_type_id, :name, :reference_kg, :display_unit, :source, :source_url, 2024, true, now(), now())"
            ),
            {
                "key": key,
                "waste_type_id": tetra.id,
                "name": name,
                "reference_kg": round(reference_kg, 6),
                "display_unit": unit,
                "source": "Composición media publicada por Tetra Pak para envases asépticos: 70% cartón, 25% polímeros y 5% aluminio. La composición varía según formato; contenido estimado, no recuperación verificada.",
                "source_url": TETRA_PAK_URL,
            },
        )


def downgrade() -> None:
    # The records are harmless display factors; leave them intact so an admin
    # edit made after the migration is not silently discarded.
    pass
