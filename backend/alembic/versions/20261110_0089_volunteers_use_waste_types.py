"""Use the shared waste type catalog for volunteer contributions.

Revision ID: 20261110_0089
Revises: 20261110_0088
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20261110_0089"
down_revision: str | None = "20261110_0088"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Preserve the volunteer catalog by adding any missing names to the shared catalog.
    op.execute(
        """
        INSERT INTO waste_types (name, description, is_recyclable)
        SELECT trim(rm.name), rm.description, TRUE
        FROM recyclable_materials rm
        WHERE NOT EXISTS (
            SELECT 1 FROM waste_types wt
            WHERE lower(trim(wt.name)) = lower(trim(rm.name))
        )
        """
    )
    op.drop_constraint(
        "material_contribution_items_material_id_fkey",
        "material_contribution_items",
        type_="foreignkey",
    )
    op.execute(
        """
        UPDATE material_contribution_items item
        SET material_id = wt.id
        FROM recyclable_materials rm
        JOIN waste_types wt ON lower(trim(wt.name)) = lower(trim(rm.name))
        WHERE item.material_id = rm.id
        """
    )
    op.create_foreign_key(
        "fk_material_contribution_items_waste_type",
        "material_contribution_items",
        "waste_types",
        ["material_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_index("idx_recyclable_materials_active_order", table_name="recyclable_materials")
    op.drop_table("recyclable_materials")


def downgrade() -> None:
    op.create_table(
        "recyclable_materials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("name_normalized", sa.String(100), nullable=False),
        sa.Column("category", sa.String(100)),
        sa.Column("unit", sa.String(8), nullable=False, server_default="kg"),
        sa.Column("description", sa.Text()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint("unit in ('kg')", name="ck_recyclable_materials_unit"),
        sa.UniqueConstraint("name_normalized", name="uq_recyclable_materials_name_normalized"),
    )
    op.create_index("idx_recyclable_materials_active_order", "recyclable_materials", ["active", "sort_order"])
    op.execute(
        """
        INSERT INTO recyclable_materials
            (name, name_normalized, description, active, sort_order)
        SELECT DISTINCT ON (lower(trim(wt.name)))
            left(trim(wt.name), 100), lower(trim(left(wt.name, 100))), wt.description, TRUE, 0
        FROM waste_types wt
        JOIN material_contribution_items item ON item.material_id = wt.id
        ORDER BY lower(trim(wt.name)), wt.name
        """
    )
    op.drop_constraint(
        "fk_material_contribution_items_waste_type",
        "material_contribution_items",
        type_="foreignkey",
    )
    op.execute(
        """
        UPDATE material_contribution_items item
        SET material_id = rm.id
        FROM waste_types wt
        JOIN recyclable_materials rm ON lower(trim(rm.name)) = lower(trim(wt.name))
        WHERE item.material_id = wt.id
        """
    )
    op.create_foreign_key(
        "material_contribution_items_material_id_fkey",
        "material_contribution_items",
        "recyclable_materials",
        ["material_id"],
        ["id"],
        ondelete="RESTRICT",
    )
