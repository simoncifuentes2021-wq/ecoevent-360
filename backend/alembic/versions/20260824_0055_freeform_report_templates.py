"""Add reusable freeform report templates.

Revision ID: 20260824_0055
Revises: 20260824_0054
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260824_0055"
down_revision = "20260824_0054"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "report_template_layouts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("description", sa.String(500)),
        sa.Column(
            "pages", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("name", name="uq_report_template_layouts_name"),
    )
    op.execute("alter table report_template_layouts enable row level security")
    op.execute("alter table report_template_layouts force row level security")
    op.execute(
        "create policy report_template_layouts_admin on report_template_layouts for all using (app_is_admin()) with check (app_is_admin())"
    )


def downgrade() -> None:
    op.drop_table("report_template_layouts")
