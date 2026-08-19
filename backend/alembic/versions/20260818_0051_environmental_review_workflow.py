"""Add environmental action review workflow.

Revision ID: 20260818_0051
Revises: 20260818_0050
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260818_0051"
down_revision = "20260818_0050"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.add_column(
        "environmental_actions",
        sa.Column("review_status", sa.String(30), server_default="DRAFT", nullable=False),
    )
    op.add_column(
        "environmental_actions",
        sa.Column("review_revision", sa.Integer(), server_default="1", nullable=False),
    )
    op.add_column("environmental_actions", sa.Column("submitted_at", sa.DateTime()))
    op.add_column(
        "environmental_actions",
        sa.Column("submitted_by", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
    )
    op.add_column("environmental_actions", sa.Column("reviewed_at", sa.DateTime()))
    op.add_column(
        "environmental_actions",
        sa.Column("reviewed_by", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
    )
    op.add_column("environmental_actions", sa.Column("review_comment", sa.Text()))
    op.create_check_constraint(
        "ck_environmental_action_review_status",
        "environmental_actions",
        "review_status in ('DRAFT','IN_REVIEW','APPROVED','CHANGES_REQUESTED','REJECTED')",
    )
    op.create_table(
        "environmental_action_reviews",
        sa.Column("id", UUID, server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column(
            "action_id",
            UUID,
            sa.ForeignKey("environmental_actions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("decision", sa.String(30), nullable=False),
        sa.Column("comment", sa.Text()),
        sa.Column("actor_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.CheckConstraint(
            "decision in ('SUBMITTED','APPROVED','CHANGES_REQUESTED','REJECTED','INVALIDATED')",
            name="ck_environmental_action_review_decision",
        ),
    )
    op.create_index(
        "idx_environmental_action_reviews_action_id",
        "environmental_action_reviews",
        ["action_id"],
    )
    op.execute("alter table environmental_action_reviews enable row level security")
    op.execute("alter table environmental_action_reviews force row level security")
    op.execute(
        "create policy environmental_action_reviews_select on environmental_action_reviews for select using (exists (select 1 from environmental_actions a where a.id = action_id and app_can_view_event(a.event_id)))"
    )
    op.execute(
        "create policy environmental_action_reviews_write on environmental_action_reviews for all using (exists (select 1 from environmental_actions a where a.id = action_id and (app_is_admin() or app_current_role() = 'SUPERVISOR') and app_can_view_event(a.event_id))) with check (exists (select 1 from environmental_actions a where a.id = action_id and (app_is_admin() or app_current_role() = 'SUPERVISOR') and app_can_view_event(a.event_id)))"
    )


def downgrade() -> None:
    op.drop_table("environmental_action_reviews")
    op.drop_constraint("ck_environmental_action_review_status", "environmental_actions")
    for column in (
        "review_comment",
        "reviewed_by",
        "reviewed_at",
        "submitted_by",
        "submitted_at",
        "review_revision",
        "review_status",
    ):
        op.drop_column("environmental_actions", column)
