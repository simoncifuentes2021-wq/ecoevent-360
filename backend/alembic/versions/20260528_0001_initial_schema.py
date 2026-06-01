"""baseline existing SQL schema

Revision ID: 20260528_0001
Revises:
Create Date: 2026-05-28

This project already has a PostgreSQL schema created from
base_datos/ecoevent_360_schema.sql. The migration is intentionally empty so
Alembic can mark that existing schema as the baseline without recreating or
dropping tables.
"""

revision = "20260528_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

