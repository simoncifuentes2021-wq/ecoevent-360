"""Add source-backed eco-equivalence factors for collection records.

Revision ID: 20261002_0069
Revises: 20261001_0068
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261002_0069"
down_revision = "20261001_0068"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "waste_collection_equivalence_factors",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("waste_type_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("waste_types.id", ondelete="CASCADE")),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("reference_kg", sa.Numeric(14, 6), nullable=False),
        sa.Column("display_unit", sa.String(120), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text()),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.UniqueConstraint("key", name="uq_waste_collection_equivalence_factors_key"),
        sa.UniqueConstraint("waste_type_id", name="uq_waste_collection_equivalence_waste_type"),
        sa.CheckConstraint("reference_kg > 0", name="ck_waste_collection_equivalence_reference_positive"),
        sa.CheckConstraint(
            "(kind = 'FAMILY_DAYS' and waste_type_id is null) or "
            "(kind = 'MATERIAL_UNITS' and waste_type_id is not null)",
            name="ck_waste_collection_equivalence_scope",
        ),
    )
    op.create_index(
        "idx_waste_collection_equivalence_factors_active",
        "waste_collection_equivalence_factors",
        ["is_active", "kind"],
    )
    op.execute("alter table waste_collection_equivalence_factors enable row level security")
    op.execute("alter table waste_collection_equivalence_factors force row level security")
    op.execute(
        "create policy waste_collection_equivalence_factors_read "
        "on waste_collection_equivalence_factors for select "
        "using (app_current_role() in ('SUPER_ADMIN','ADMIN','SUPERVISOR','CLIENT'))"
    )
    op.execute(
        "create policy waste_collection_equivalence_factors_write "
        "on waste_collection_equivalence_factors for all "
        "using (app_is_admin()) with check (app_is_admin())"
    )


def downgrade() -> None:
    op.drop_table("waste_collection_equivalence_factors")
