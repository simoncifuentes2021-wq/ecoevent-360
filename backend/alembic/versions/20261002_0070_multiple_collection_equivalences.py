"""Allow and seed multiple eco-equivalences per collection material.

Revision ID: 20261002_0070
Revises: 20261002_0069
"""

from __future__ import annotations

import re
import unicodedata

from alembic import op
import sqlalchemy as sa

revision = "20261002_0070"
down_revision = "20261002_0069"
branch_labels = None
depends_on = None

WARM_URL = "https://www.epa.gov/system/files/documents/2023-12/warm_containers_packaging_and_non-durable_goods_materials_v16_dec.pdf"
EPA_EQUIVALENCIES_URL = "https://www.epa.gov/energy/greenhouse-gas-equivalencies-calculator"
TETRA_PAK_URL = "https://www.tetrapak.com/sustainability/planet/packaging-material"


def _plain(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    return re.sub(r"[^a-z0-9]+", " ", "".join(char for char in value if not unicodedata.combining(char))).strip()


def upgrade() -> None:
    op.drop_constraint(
        "uq_waste_collection_equivalence_waste_type",
        "waste_collection_equivalence_factors",
        type_="unique",
    )

    bind = op.get_bind()
    materials = bind.execute(sa.text("select id, name from waste_types")).all()
    specs = [
        {
            "match": lambda name: name == "latas de aluminio",
            "suffix": "ALUMINUM_KWH",
            "name": "Ahorro energético potencial del aluminio reciclado",
            "rate": 49.35,
            "unit": "kWh potenciales",
            "source": "EPA WARM v16: ahorro energético neto estimado para latas de aluminio; factor de referencia de EE.UU. Es una estimación potencial si el material se recicla.",
            "url": WARM_URL,
            "year": 2023,
            "active": True,
        },
        {
            "match": lambda name: name.endswith(" pet") or name == "pet",
            "suffix": "PET_PHONE_CHARGES",
            "name": "Impacto climático equivalente del PET reciclado",
            "rate": 92.0,
            "unit": "cargas completas de celular equivalentes",
            "source": "Equivalencia potencial basada en beneficio climático EPA WARM v16 para PET y emisiones por carga del calculador EPA. Supone reciclaje; cargas y factores de electricidad usan referencias de EE.UU.",
            "url": EPA_EQUIVALENCIES_URL,
            "year": 2023,
            "active": True,
        },
        {
            "match": lambda name: name.endswith(" pet") or name == "pet",
            "suffix": "PET_KWH",
            "name": "Ahorro energético potencial del PET reciclado",
            "rate": 9.24,
            "unit": "kWh potenciales",
            "source": "EPA WARM v16: ahorro energético neto estimado para PET. Factor de referencia de EE.UU.; representa un escenario potencial de reciclaje.",
            "url": WARM_URL,
            "year": 2023,
            "active": True,
        },
        {
            "match": lambda name: "polipropileno" in name,
            "suffix": "PP_LED_HOURS",
            "name": "Iluminación LED equivalente del polipropileno reciclado",
            "rate": 1438.0,
            "unit": "horas de iluminación LED de 10 W equivalentes",
            "source": "EPA WARM v16: ahorro energético estimado para polipropileno, convertido a horas de una ampolleta LED de 10 W. Factor de referencia de EE.UU.; potencial si se recicla.",
            "url": WARM_URL,
            "year": 2023,
            "active": True,
        },
        {
            "match": lambda name: name == "residuos organicos",
            "suffix": "FOOD_WASTE_CO2E",
            "name": "Emisiones evitadas si los residuos alimentarios se compostan",
            "rate": 0.72,
            "unit": "kg CO₂e potenciales",
            "source": "EPA WARM v16: diferencia estimada entre compostaje y relleno sanitario para residuos alimentarios. Solo es aplicable a residuos de alimentos y si se confirma el compostaje; referencia de EE.UU.",
            "url": "https://www.epa.gov/warm/versions-waste-reduction-model-warm",
            "year": 2023,
            "active": False,
        },
        {
            "match": lambda name: name == "vidrio",
            "suffix": "GLASS_KWH",
            "name": "Ahorro energético potencial del vidrio reciclado",
            "rate": 0.69,
            "unit": "kWh potenciales",
            "source": "EPA WARM v16: ahorro energético neto estimado para envases de vidrio. Factor de referencia de EE.UU.; potencial si se recicla.",
            "url": WARM_URL,
            "year": 2023,
            "active": True,
        },
        {
            "match": lambda name: name == "carton",
            "suffix": "CORRUGATED_PHONE_CHARGES",
            "name": "Impacto climático equivalente del cartón corrugado reciclado",
            "rate": 279.0,
            "unit": "cargas completas de celular equivalentes",
            "source": "Equivalencia potencial basada en beneficio climático EPA WARM v16 para cartón corrugado y emisiones por carga del calculador EPA. Supone reciclaje; cargas y factores de electricidad usan referencias de EE.UU.",
            "url": EPA_EQUIVALENCIES_URL,
            "year": 2023,
            "active": True,
        },
        {
            "match": lambda name: name == "carton",
            "suffix": "CORRUGATED_KWH",
            "name": "Ahorro energético potencial del cartón corrugado reciclado",
            "rate": 4.88,
            "unit": "kWh potenciales",
            "source": "EPA WARM v16: ahorro energético neto estimado para cartón corrugado. Factor de referencia de EE.UU.; potencial si se recicla.",
            "url": WARM_URL,
            "year": 2023,
            "active": True,
        },
        {
            "match": lambda name: name in {"tetrapack", "tetrapak", "tetra pak", "envase larga vida"},
            "suffix": "TETRA_FIBER",
            "name": "Fibra de cartón contenida en envases asépticos",
            "rate": 0.70,
            "unit": "kg de fibra de cartón estimados",
            "source": "Composición media publicada por Tetra Pak para envases asépticos: 70% cartón, 25% polímeros y 5% aluminio. La composición varía según formato; contenido estimado, no recuperación verificada.",
            "url": TETRA_PAK_URL,
            "year": 2024,
            "active": True,
        },
        {
            "match": lambda name: name in {"tetrapack", "tetrapak", "tetra pak", "envase larga vida"},
            "suffix": "TETRA_POLYMERS",
            "name": "Polímeros contenidos en envases asépticos",
            "rate": 0.25,
            "unit": "kg de polímeros estimados",
            "source": "Composición media publicada por Tetra Pak para envases asépticos: 70% cartón, 25% polímeros y 5% aluminio. La composición varía según formato; contenido estimado, no recuperación verificada.",
            "url": TETRA_PAK_URL,
            "year": 2024,
            "active": True,
        },
        {
            "match": lambda name: name in {"tetrapack", "tetrapak", "tetra pak", "envase larga vida"},
            "suffix": "TETRA_ALUMINUM",
            "name": "Aluminio contenido en envases asépticos",
            "rate": 0.05,
            "unit": "kg de aluminio estimados",
            "source": "Composición media publicada por Tetra Pak para envases asépticos: 70% cartón, 25% polímeros y 5% aluminio. La composición varía según formato; contenido estimado, no recuperación verificada.",
            "url": TETRA_PAK_URL,
            "year": 2024,
            "active": True,
        },
    ]

    existing = set(bind.execute(sa.text("select key from waste_collection_equivalence_factors")).scalars())
    for material in materials:
        normalized = _plain(material.name)
        for spec in specs:
            if not spec["match"](normalized):
                continue
            key = f"MATERIAL_{material.id.hex.upper()}_{spec['suffix']}"
            if key in existing:
                continue
            bind.execute(
                sa.text(
                    "insert into waste_collection_equivalence_factors "
                    "(id, key, kind, waste_type_id, name, reference_kg, display_unit, source, source_url, year, is_active, created_at, updated_at) "
                    "values (uuid_generate_v4(), :key, 'MATERIAL_UNITS', :waste_type_id, :name, :reference_kg, :display_unit, :source, :source_url, :year, :is_active, now(), now())"
                ),
                {
                    "key": key,
                    "waste_type_id": material.id,
                    "name": spec["name"],
                    "reference_kg": round(1 / spec["rate"], 6),
                    "display_unit": spec["unit"],
                    "source": spec["source"],
                    "source_url": spec["url"],
                    "year": spec["year"],
                    "is_active": spec["active"],
                },
            )
            existing.add(key)


def downgrade() -> None:
    op.create_unique_constraint(
        "uq_waste_collection_equivalence_waste_type",
        "waste_collection_equivalence_factors",
        ["waste_type_id"],
    )
