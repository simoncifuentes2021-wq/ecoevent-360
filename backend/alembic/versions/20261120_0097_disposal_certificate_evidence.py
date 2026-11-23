"""Link disposal certificates to event evidence."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20261120_0097"
down_revision: str | None = "20261120_0096"
branch_labels: str | Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "waste_disposal_certificates",
        sa.Column("evidence_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_waste_disposal_certificates_evidence",
        "waste_disposal_certificates",
        "evidences",
        ["evidence_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_waste_disposal_certificates_evidence",
        "waste_disposal_certificates",
        type_="foreignkey",
    )
    op.drop_column("waste_disposal_certificates", "evidence_id")
