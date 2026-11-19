"""Allow field staff to attach evidence to contributions at assigned points.

Revision ID: 20261110_0091
Revises: 20261110_0090
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20261110_0091"
down_revision: str | None = "20261110_0090"
branch_labels: str | Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute("""
        CREATE POLICY evidences_field_staff_contribution_select ON evidences FOR SELECT USING (
          volunteer_contribution_id IS NOT NULL AND EXISTS (
            SELECT 1 FROM material_contributions mc
            WHERE mc.id = evidences.volunteer_contribution_id
              AND app_field_staff_can_access_activation(mc.activation_id)
          )
        )
    """)
    op.execute("""
        CREATE POLICY evidences_field_staff_contribution_insert ON evidences FOR INSERT WITH CHECK (
          volunteer_contribution_id IS NOT NULL AND EXISTS (
            SELECT 1 FROM material_contributions mc
            JOIN recycling_activations a ON a.id = mc.activation_id
            WHERE mc.id = evidences.volunteer_contribution_id
              AND a.id = nullif(current_setting('app.field_staff_activation_id', true), '')::uuid
              AND a.event_id = evidences.event_id
              AND app_field_staff_can_access_activation(a.id)
          )
        )
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS evidences_field_staff_contribution_insert ON evidences")
    op.execute("DROP POLICY IF EXISTS evidences_field_staff_contribution_select ON evidences")
