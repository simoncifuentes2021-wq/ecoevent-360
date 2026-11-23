"""Scope disposal certificates by event with row-level security."""

from collections.abc import Sequence

from alembic import op


revision: str = "20261120_0098"
down_revision: str | None = "20261120_0097"
branch_labels: str | Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE waste_disposal_certificates ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY waste_disposal_certificates_event_access
        ON waste_disposal_certificates
        FOR ALL
        USING (app_can_view_event(event_id))
        WITH CHECK (app_can_view_event(event_id))
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS waste_disposal_certificates_event_access ON waste_disposal_certificates"
    )
    op.execute("ALTER TABLE waste_disposal_certificates DISABLE ROW LEVEL SECURITY")
