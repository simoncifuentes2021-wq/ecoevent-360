"""Add encrypted Super Admin Google Calendar connection."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20261124_0100"
down_revision: str | None = "20261123_0099"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "google_calendar_connections",
        sa.Column("connection_key", sa.String(length=24), primary_key=True),
        sa.Column("account_email", sa.String(length=320), nullable=False),
        sa.Column("refresh_token_encrypted", sa.Text(), nullable=False),
        sa.Column("granted_scopes", sa.Text(), nullable=False),
        sa.Column("connected_by", sa.UUID(), nullable=True),
        sa.Column("connected_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["connected_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.execute("ALTER TABLE google_calendar_connections ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY google_calendar_super_admin_only ON google_calendar_connections "
        "FOR ALL USING (app_current_role() = 'SUPER_ADMIN') "
        "WITH CHECK (app_current_role() = 'SUPER_ADMIN')"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS google_calendar_super_admin_only ON google_calendar_connections")
    op.drop_table("google_calendar_connections")
