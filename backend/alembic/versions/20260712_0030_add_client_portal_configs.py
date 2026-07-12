"""add client portal configs

Revision ID: 20260712_0030
Revises: 20260709_0029
Create Date: 2026-07-12 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260712_0030"
down_revision = "20260709_0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "client_portal_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scope", sa.String(length=30), nullable=False, server_default=sa.text("'EVENT'")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("client_id", "event_id", name="uq_client_portal_configs_client_event"),
    )
    op.create_index("idx_client_portal_configs_client_id", "client_portal_configs", ["client_id"])
    op.create_index("idx_client_portal_configs_event_id", "client_portal_configs", ["event_id"])

    op.create_table(
        "client_portal_sections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("config_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("client_portal_configs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("section_key", sa.String(length=100), nullable=False),
        sa.Column("label", sa.String(length=160), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.UniqueConstraint("config_id", "section_key", name="uq_client_portal_sections_config_key"),
    )
    op.create_index("idx_client_portal_sections_config_id", "client_portal_sections", ["config_id"])

    op.create_table(
        "client_portal_widgets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("config_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("client_portal_configs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("widget_key", sa.String(length=120), nullable=False),
        sa.Column("section_key", sa.String(length=100), nullable=False),
        sa.Column("label", sa.String(length=180), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("visibility_config", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.UniqueConstraint("config_id", "widget_key", name="uq_client_portal_widgets_config_key"),
    )
    op.create_index("idx_client_portal_widgets_config_id", "client_portal_widgets", ["config_id"])
    op.create_index("idx_client_portal_widgets_section_key", "client_portal_widgets", ["section_key"])


def downgrade() -> None:
    op.drop_index("idx_client_portal_widgets_section_key", table_name="client_portal_widgets")
    op.drop_index("idx_client_portal_widgets_config_id", table_name="client_portal_widgets")
    op.drop_table("client_portal_widgets")
    op.drop_index("idx_client_portal_sections_config_id", table_name="client_portal_sections")
    op.drop_table("client_portal_sections")
    op.drop_index("idx_client_portal_configs_event_id", table_name="client_portal_configs")
    op.drop_index("idx_client_portal_configs_client_id", table_name="client_portal_configs")
    op.drop_table("client_portal_configs")
