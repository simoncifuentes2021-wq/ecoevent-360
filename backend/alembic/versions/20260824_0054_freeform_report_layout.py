"""Add freeform report pages and elements.

Revision ID: 20260824_0054
Revises: 20260822_0053
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260824_0054"
down_revision = "20260822_0053"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.add_column(
        "reports",
        sa.Column("composition_mode", sa.String(20), nullable=False, server_default="AUTO"),
    )
    op.create_check_constraint(
        "ck_reports_composition_mode", "reports", "composition_mode in ('AUTO','FREEFORM')"
    )
    op.create_table(
        "report_pages",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column(
            "report_id", UUID, sa.ForeignKey("reports.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(180)),
        sa.Column("width", sa.Float(), nullable=False, server_default="1000"),
        sa.Column("height", sa.Float(), nullable=False, server_default="1414"),
        sa.Column("background", sa.String(32), nullable=False, server_default="#FFFFFF"),
        sa.Column("background_image", sa.Text()),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("report_id", "page_number", name="uq_report_pages_report_number"),
        sa.CheckConstraint("page_number > 0", name="ck_report_pages_number"),
        sa.CheckConstraint("width > 0 and height > 0", name="ck_report_pages_dimensions"),
    )
    op.create_index("idx_report_pages_report_number", "report_pages", ["report_id", "page_number"])
    op.create_table(
        "report_elements",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column(
            "page_id", UUID, sa.ForeignKey("report_pages.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("x", sa.Float(), nullable=False),
        sa.Column("y", sa.Float(), nullable=False),
        sa.Column("width", sa.Float(), nullable=False),
        sa.Column("height", sa.Float(), nullable=False),
        sa.Column("rotation", sa.Float(), nullable=False, server_default="0"),
        sa.Column("z_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("visible", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "content", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column(
            "style", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column("data_binding", postgresql.JSONB()),
        sa.Column(
            "metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "type in ('TEXT','TITLE','KPI','IMAGE','CHART','SHAPE')", name="ck_report_elements_type"
        ),
        sa.CheckConstraint("x >= 0 and y >= 0", name="ck_report_elements_position"),
        sa.CheckConstraint("width > 0 and height > 0", name="ck_report_elements_dimensions"),
        sa.CheckConstraint(
            "rotation >= -360 and rotation <= 360", name="ck_report_elements_rotation"
        ),
    )
    op.create_index("idx_report_elements_page_z", "report_elements", ["page_id", "z_index"])
    for table in ("report_pages", "report_elements"):
        op.execute(f"alter table {table} enable row level security")
        op.execute(f"alter table {table} force row level security")
    op.execute(
        "create policy report_pages_select on report_pages for select using (exists (select 1 from reports r where r.id=report_pages.report_id and app_can_view_event(r.event_id) and (app_current_role() <> 'CLIENT' or r.status <> 'DRAFT')))"
    )
    op.execute(
        "create policy report_pages_write on report_pages for all using (app_is_admin() and exists (select 1 from reports r where r.id=report_pages.report_id and app_can_view_event(r.event_id))) with check (app_is_admin() and exists (select 1 from reports r where r.id=report_pages.report_id and app_can_view_event(r.event_id)))"
    )
    op.execute(
        "create policy report_elements_select on report_elements for select using (exists (select 1 from report_pages p join reports r on r.id=p.report_id where p.id=report_elements.page_id and app_can_view_event(r.event_id) and (app_current_role() <> 'CLIENT' or r.status <> 'DRAFT')))"
    )
    op.execute(
        "create policy report_elements_write on report_elements for all using (app_is_admin() and exists (select 1 from report_pages p join reports r on r.id=p.report_id where p.id=report_elements.page_id and app_can_view_event(r.event_id))) with check (app_is_admin() and exists (select 1 from report_pages p join reports r on r.id=p.report_id where p.id=report_elements.page_id and app_can_view_event(r.event_id)))"
    )


def downgrade() -> None:
    op.drop_table("report_elements")
    op.drop_table("report_pages")
    op.drop_constraint("ck_reports_composition_mode", "reports", type_="check")
    op.drop_column("reports", "composition_mode")
