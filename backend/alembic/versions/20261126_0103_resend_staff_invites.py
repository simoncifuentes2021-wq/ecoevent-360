"""Track Resend email notifications for event staff invitations."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20261126_0103"
down_revision: str | None = "20261125_0102"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "event_staff",
        sa.Column("resend_invitation_status", sa.String(length=16), server_default="PENDING", nullable=False),
    )
    op.add_column("event_staff", sa.Column("resend_invitation_error", sa.Text(), nullable=True))
    op.add_column("event_staff", sa.Column("resend_invitation_id", sa.String(length=128), nullable=True))
    op.add_column("event_staff", sa.Column("resend_invitation_accepted_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("event_staff", "resend_invitation_accepted_at")
    op.drop_column("event_staff", "resend_invitation_id")
    op.drop_column("event_staff", "resend_invitation_error")
    op.drop_column("event_staff", "resend_invitation_status")
