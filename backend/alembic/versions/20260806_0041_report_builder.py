"""Add the show-aware professional report builder.

Revision ID: 20260806_0041
Revises: 20260806_0040
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260806_0041"
down_revision = "20260806_0040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "reports", sa.Column("scope", sa.String(20), server_default="EVENT", nullable=False)
    )
    op.add_column("reports", sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("reports", sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column(
        "reports",
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )
    op.add_column(
        "reports", sa.Column("edit_version", sa.Integer(), server_default="1", nullable=False)
    )
    op.create_foreign_key(
        "fk_reports_event_session",
        "reports",
        "event_sessions",
        ["event_id", "session_id"],
        ["event_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_reports_created_by_users",
        "reports",
        "users",
        ["created_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        "ck_reports_scope_session",
        "reports",
        "(scope = 'EVENT' and session_id is null) or (scope = 'SHOW' and session_id is not null)",
    )
    op.create_check_constraint("ck_reports_edit_version", "reports", "edit_version > 0")
    op.create_index("idx_reports_session_id", "reports", ["session_id"])
    op.execute("drop policy if exists reports_rls on reports")
    op.execute(
        "create policy reports_select on reports for select using (app_can_view_event(event_id) and (app_current_role() <> 'CLIENT' or status <> 'DRAFT'))"
    )
    op.execute(
        "create policy reports_write on reports for all using (app_is_admin() and app_can_view_event(event_id)) with check (app_is_admin() and app_can_view_event(event_id))"
    )

    op.create_table(
        "report_sections",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("uuid_generate_v4()"),
            primary_key=True,
        ),
        sa.Column(
            "report_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("section_key", sa.String(100), nullable=False),
        sa.Column("section_type", sa.String(40), nullable=False),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column(
            "content", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
        sa.Column(
            "source_snapshot",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "source_metadata",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("is_custom", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("edit_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("report_id", "section_key", name="uq_report_sections_report_key"),
        sa.CheckConstraint("sort_order >= 0", name="ck_report_sections_sort_order"),
        sa.CheckConstraint("edit_version > 0", name="ck_report_sections_edit_version"),
    )
    op.create_index(
        "idx_report_sections_report_order", "report_sections", ["report_id", "sort_order"]
    )
    op.create_table(
        "report_evidences",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("uuid_generate_v4()"),
            primary_key=True,
        ),
        sa.Column(
            "report_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "section_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("report_sections.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "evidence_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("evidences.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("caption", sa.String(500)),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("report_id", "evidence_id", name="uq_report_evidences_report_evidence"),
        sa.CheckConstraint("sort_order >= 0", name="ck_report_evidences_sort_order"),
    )
    op.create_index(
        "idx_report_evidences_report_order", "report_evidences", ["report_id", "sort_order"]
    )
    op.create_table(
        "report_revisions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("uuid_generate_v4()"),
            primary_key=True,
        ),
        sa.Column(
            "report_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column("note", sa.String(500)),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("report_id", "revision_number", name="uq_report_revisions_number"),
        sa.CheckConstraint("revision_number > 0", name="ck_report_revisions_number"),
    )
    op.create_index("idx_report_revisions_report", "report_revisions", ["report_id"])
    for table in ("report_sections", "report_evidences", "report_revisions"):
        op.execute(f"alter table {table} enable row level security")
        op.execute(f"alter table {table} force row level security")
        op.execute(
            f"create policy {table}_select on {table} for select using (exists (select 1 from reports r where r.id = report_id and app_can_view_event(r.event_id) and (app_current_role() <> 'CLIENT' or r.status <> 'DRAFT')))"
        )
        op.execute(
            f"create policy {table}_write on {table} for all using (app_is_admin() and exists (select 1 from reports r where r.id = report_id and app_can_view_event(r.event_id))) with check (app_is_admin() and exists (select 1 from reports r where r.id = report_id and app_can_view_event(r.event_id)))"
        )
    op.execute("drop policy report_revisions_select on report_revisions")
    op.execute(
        "create policy report_revisions_select on report_revisions for select using (app_is_admin() and exists (select 1 from reports r where r.id = report_id and app_can_view_event(r.event_id)))"
    )


def downgrade() -> None:
    for table in ("report_revisions", "report_evidences", "report_sections"):
        op.drop_table(table)
    op.execute("drop policy if exists reports_write on reports")
    op.execute("drop policy if exists reports_select on reports")
    op.execute(
        "create policy reports_rls on reports for all using (app_can_view_event(event_id)) with check (app_can_view_event(event_id))"
    )
    op.drop_index("idx_reports_session_id", table_name="reports")
    op.drop_constraint("ck_reports_edit_version", "reports", type_="check")
    op.drop_constraint("ck_reports_scope_session", "reports", type_="check")
    op.drop_constraint("fk_reports_created_by_users", "reports", type_="foreignkey")
    op.drop_constraint("fk_reports_event_session", "reports", type_="foreignkey")
    for column in ("edit_version", "updated_at", "created_by", "session_id", "scope"):
        op.drop_column("reports", column)
