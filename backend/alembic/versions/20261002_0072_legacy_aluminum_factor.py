"""Keep the demo's legacy aluminum stream covered by its energy comparison.

Revision ID: 20261002_0072
Revises: 20261002_0071
"""

from __future__ import annotations

import re
import unicodedata

from alembic import op
import sqlalchemy as sa

revision = "20261002_0072"
down_revision = "20261002_0071"
branch_labels = None
depends_on = None


def _plain(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    return re.sub(r"[^a-z0-9]+", " ", "".join(char for char in value if not unicodedata.combining(char))).strip()


def upgrade() -> None:
    bind = op.get_bind()
    material = next(
        (row for row in bind.execute(sa.text("select id, name from waste_types")).all() if _plain(row.name) == "aluminio"),
        None,
    )
    if material is None:
        return

    key = f"MATERIAL_{material.id.hex.upper()}_ALUMINUM_LEGACY_KWH"
    if bind.scalar(sa.text("select 1 from waste_collection_equivalence_factors where key = :key"), {"key": key}):
        return

    bind.execute(
        sa.text(
            "insert into waste_collection_equivalence_factors "
            "(id, key, kind, waste_type_id, name, reference_kg, display_unit, source, source_url, year, is_active, created_at, updated_at) "
            "values (uuid_generate_v4(), :key, 'MATERIAL_UNITS', :waste_type_id, :name, :reference_kg, :display_unit, :source, :source_url, 2023, true, now(), now())"
        ),
        {
            "key": key,
            "waste_type_id": material.id,
            "name": "Ahorro energético potencial del aluminio valorizado",
            "reference_kg": round(1 / 49.35, 6),
            "display_unit": "kWh potenciales",
            "source": "EPA WARM v16 estima el ahorro energético para latas de aluminio. Este factor se ofrece como referencia para el flujo heredado llamado Aluminio; el resultado depende de que corresponda a aluminio reciclable y de su valorización efectiva.",
            "source_url": "https://www.epa.gov/system/files/documents/2023-12/warm_containers_packaging_and_non-durable_goods_materials_v16_dec.pdf",
        },
    )


def downgrade() -> None:
    # Preserve the factor if it has been edited from the administration UI.
    pass
