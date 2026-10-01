"""Allow event members to manage collection point waste types.

Revision ID: 20261001_0068
Revises: 20260930_0067
"""
from collections.abc import Sequence

from alembic import op

revision: str = "20261001_0068"
down_revision: str | None = "20260930_0067"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE POLICY waste_collection_point_types_event_access
        ON waste_collection_point_types FOR ALL
        USING (
          EXISTS (
            SELECT 1 FROM waste_collection_points p
            WHERE p.id = collection_point_id AND app_can_view_event(p.event_id)
          )
        )
        WITH CHECK (
          EXISTS (
            SELECT 1 FROM waste_collection_points p
            WHERE p.id = collection_point_id AND app_can_view_event(p.event_id)
          )
        )
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS waste_collection_point_types_event_access ON waste_collection_point_types")
