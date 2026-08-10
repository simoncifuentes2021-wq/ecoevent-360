"""Add premium immutable report publications.

Revision ID: 20260807_0043
Revises: 20260806_0042
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260807_0043"
down_revision = "20260806_0042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "reports",
        sa.Column(
            "template_key", sa.String(40), nullable=False, server_default="ENVIRONMENTAL_PREMIUM"
        ),
    )
    op.add_column(
        "reports",
        sa.Column(
            "theme", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
    )
    op.create_table(
        "report_publications",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "report_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "revision_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("report_revisions.id", ondelete="SET NULL"),
        ),
        sa.Column("publication_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="GENERATED"),
        sa.Column("storage_key", sa.Text(), nullable=False, unique=True),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("theme_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column(
            "generated_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column("generated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column(
            "delivered_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column("delivered_at", sa.DateTime()),
        sa.Column("idempotency_key", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint(
            "report_id", "publication_number", name="uq_report_publications_number"
        ),
        sa.UniqueConstraint(
            "report_id", "idempotency_key", name="uq_report_publications_idempotency"
        ),
        sa.CheckConstraint("publication_number > 0", name="ck_report_publications_number"),
        sa.CheckConstraint("file_size > 100", name="ck_report_publications_file_size"),
        sa.CheckConstraint("page_count > 0", name="ck_report_publications_page_count"),
    )
    op.create_index(
        "idx_report_publications_report", "report_publications", ["report_id", "publication_number"]
    )
    op.create_index("idx_report_publications_status", "report_publications", ["status"])
    op.execute("alter table report_publications enable row level security")
    op.execute("alter table report_publications force row level security")
    op.execute(
        "create policy report_publications_select on report_publications for select using (exists (select 1 from reports r where r.id=report_publications.report_id and app_can_view_event(r.event_id)) and (app_current_role() <> 'CLIENT' or report_publications.status='DELIVERED'))"
    )
    op.execute(
        "create policy report_publications_write on report_publications for all using (app_is_admin() and exists (select 1 from reports r where r.id=report_publications.report_id and app_can_view_event(r.event_id))) with check (app_is_admin() and exists (select 1 from reports r where r.id=report_publications.report_id and app_can_view_event(r.event_id)))"
    )


def downgrade() -> None:
    op.drop_table("report_publications")
    op.drop_column("reports", "theme")
    op.drop_column("reports", "template_key")
