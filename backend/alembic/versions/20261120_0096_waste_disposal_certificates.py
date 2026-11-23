"""Store immutable event waste disposal certificates."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20261120_0096"
down_revision: str | None = "20261120_0095"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "waste_disposal_certificates",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("certificate_number", sa.String(length=40), nullable=False),
        sa.Column("certificate_date", sa.Date(), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("generated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("generated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["generated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("certificate_number", name="uq_waste_disposal_certificate_number"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index(
        "idx_waste_disposal_certificates_event",
        "waste_disposal_certificates",
        ["event_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_waste_disposal_certificates_event", table_name="waste_disposal_certificates")
    op.drop_table("waste_disposal_certificates")
