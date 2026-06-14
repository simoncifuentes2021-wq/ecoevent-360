"""seed default catalog items

Revision ID: 20260612_0008
Revises: 20260612_0007
Create Date: 2026-06-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260612_0008"
down_revision: str | None = "20260612_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


ITEMS = (
    ("Bano quimico", "Sanitarios", "unidad"),
    ("Lavamanos", "Sanitarios", "unidad"),
    ("Contenedor 120L", "Residuos", "unidad"),
    ("Contenedor 240L", "Residuos", "unidad"),
    ("Punto limpio", "Residuos", "unidad"),
    ("Bolsa de basura", "Insumos", "unidad"),
    ("Papel higienico", "Insumos", "unidad"),
    ("Alcohol gel", "Insumos", "unidad"),
    ("Senaletica", "Senalizacion", "unidad"),
    ("Guantes", "Insumos", "par"),
    ("Escobillon", "Limpieza", "unidad"),
    ("Pala", "Limpieza", "unidad"),
    ("Bidon de agua", "Agua", "unidad"),
    ("Insumo de limpieza", "Limpieza", "unidad"),
)


def upgrade() -> None:
    bind = op.get_bind()
    for name, category, unit in ITEMS:
        bind.execute(
            sa.text(
                """
                insert into catalog_items (name, category, unit, default_unit_price, is_active)
                select cast(:name as varchar), cast(:category as varchar), cast(:unit as varchar), 0, true
                where not exists (
                    select 1 from catalog_items where lower(name) = lower(cast(:name as varchar))
                )
                """
            ),
            {"name": name, "category": category, "unit": unit},
        )


def downgrade() -> None:
    bind = op.get_bind()
    for name, _, _ in ITEMS:
        bind.execute(sa.text("delete from catalog_items where name = :name"), {"name": name})
