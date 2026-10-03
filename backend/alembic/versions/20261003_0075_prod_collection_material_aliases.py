"""Add the missing collection materials and seed factors for legacy labels.

Revision ID: 20261003_0075
Revises: 20261003_0074
"""

from __future__ import annotations

import re
import unicodedata
from uuid import UUID

from alembic import op
import sqlalchemy as sa


revision = "20261003_0075"
down_revision = "20261003_0074"
branch_labels = None
depends_on = None

WARM_URL = "https://www.epa.gov/system/files/documents/2023-12/warm_containers_packaging_and_non-durable_goods_materials_v16_dec.pdf"
EPA_EQUIVALENCIES_URL = "https://www.epa.gov/energy/greenhouse-gas-equivalencies-calculator"
TETRA_PAK_URL = "https://www.tetrapak.com/sustainability/planet/packaging-material"
ORGANIC_WARM_URL = "https://www.epa.gov/system/files/documents/2023-12/warm_organic_materials_v16_dec.pdf"


def _plain(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    return re.sub(r"[^a-z0-9]+", " ", "".join(char for char in value if not unicodedata.combining(char))).strip()


def _ensure_type(
    bind,
    name: str,
    aliases: set[str] | None = None,
    description: str = "Material reciclable recibido en Acopios.",
) -> UUID:
    rows = bind.execute(sa.text("select id, name from waste_types")).all()
    accepted = aliases or {_plain(name)}
    existing = next((row for row in rows if _plain(row.name) in accepted), None)
    if existing:
        return existing.id
    return bind.scalar(
        sa.text(
            "insert into waste_types (id, name, description, is_recyclable, created_at) "
            "values (uuid_generate_v4(), :name, :description, true, now()) returning id"
        ),
        {
            "name": name,
            "description": description,
        },
    )


def _ensure_factor(
    bind,
    waste_type_id: UUID,
    suffix: str,
    name: str,
    rate_per_kg: float,
    unit: str,
    source: str,
    source_url: str,
    year: int,
    *,
    activate: bool = False,
) -> None:
    key = f"MATERIAL_{waste_type_id.hex.upper()}_{suffix}"
    exists = bind.scalar(
        sa.text("select 1 from waste_collection_equivalence_factors where key = :key"),
        {"key": key},
    )
    if exists:
        if activate:
            bind.execute(
                sa.text(
                    "update waste_collection_equivalence_factors "
                    "set is_active = true, updated_at = now() where key = :key"
                ),
                {"key": key},
            )
        return
    bind.execute(
        sa.text(
            "insert into waste_collection_equivalence_factors "
            "(id, key, kind, waste_type_id, name, reference_kg, display_unit, source, source_url, year, is_active, created_at, updated_at) "
            "values (uuid_generate_v4(), :key, 'MATERIAL_UNITS', :waste_type_id, :name, :reference_kg, :unit, :source, :source_url, :year, true, now(), now())"
        ),
        {
            "key": key,
            "waste_type_id": waste_type_id,
            "name": name,
            "reference_kg": round(1 / rate_per_kg, 6),
            "unit": unit,
            "source": source,
            "source_url": source_url,
            "year": year,
        },
    )


def upgrade() -> None:
    bind = op.get_bind()

    # Keep existing IDs and historical names where an equivalent legacy type exists.
    _ensure_type(bind, "Plástico Flexible")
    polypropylene = _ensure_type(
        bind,
        "Plástico Polipropileno",
        {"plastico polipropileno", "polipropileno"},
    )
    cardboard = _ensure_type(bind, "Cartón")
    tetrapak = _ensure_type(
        bind,
        "Tetrapack",
        {"tetrapack", "tetrapak", "tetra pak", "envase larga vida"},
    )

    # "Orgánico" is the production catalog's legacy label; ignore QA/demo types.
    organic = _ensure_type(
        bind,
        "Residuos Orgánicos",
        {"organico", "residuos organicos"},
        "Residuo orgánico recibido en Acopios y destinado a compostaje.",
    )
    _ensure_factor(
        bind,
        organic,
        "FOOD_WASTE_CO2E",
        "Emisiones evitadas si los residuos alimentarios se compostan",
        0.72,
        "kg CO₂e potenciales",
        "EPA WARM v16: diferencia estimada entre compostaje y relleno sanitario para residuos alimentarios. La ruta a compostaje del residuo orgánico del evento fue confirmada; la estimación requiere que el flujo corresponda a residuos alimentarios. Referencia de EE.UU.",
        ORGANIC_WARM_URL,
        2023,
        activate=True,
    )

    _ensure_factor(
        bind,
        polypropylene,
        "PP_LED_HOURS",
        "Iluminación LED equivalente del polipropileno reciclado",
        1438.0,
        "horas de iluminación LED de 10 W equivalentes",
        "EPA WARM v16: ahorro energético estimado para polipropileno, convertido a horas de una ampolleta LED de 10 W. Factor de referencia de EE.UU.; potencial si se recicla.",
        WARM_URL,
        2023,
    )
    _ensure_factor(
        bind,
        cardboard,
        "CORRUGATED_KWH",
        "Ahorro energético potencial del cartón corrugado reciclado",
        4.88,
        "kWh potenciales",
        "EPA WARM v16: ahorro energético neto estimado para cartón corrugado. Factor de referencia de EE.UU.; potencial si se recicla.",
        WARM_URL,
        2023,
    )
    _ensure_factor(
        bind,
        cardboard,
        "CORRUGATED_PHONE_CHARGES",
        "Impacto climático equivalente del cartón corrugado reciclado",
        279.0,
        "cargas completas de celular equivalentes",
        "Equivalencia potencial basada en beneficio climático EPA WARM v16 para cartón corrugado y emisiones por carga del calculador EPA. Supone reciclaje; cargas y factores de electricidad usan referencias de EE.UU.",
        EPA_EQUIVALENCIES_URL,
        2023,
    )

    tetra_specs = [
        ("TETRA_FIBER", "Fibra de cartón contenida en envases asépticos", 0.70, "kg de fibra de cartón estimados"),
        ("TETRA_POLYMERS", "Polímeros contenidos en envases asépticos", 0.25, "kg de polímeros estimados"),
        ("TETRA_ALUMINUM", "Aluminio contenido en envases asépticos", 0.05, "kg de aluminio estimados"),
    ]
    tetra_source = "Composición media publicada por Tetra Pak para envases asépticos: 70% cartón, 25% polímeros y 5% aluminio. La composición varía según formato; contenido estimado, no recuperación verificada."
    for suffix, name, rate, unit in tetra_specs:
        _ensure_factor(bind, tetrapak, suffix, name, rate, unit, tetra_source, TETRA_PAK_URL, 2024)

    # Flexible plastic is available in the form; no unsupported equivalence is invented.


def downgrade() -> None:
    # Preserve administrator edits and any records created after this revision.
    pass
