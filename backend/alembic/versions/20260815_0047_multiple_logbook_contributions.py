"""Allow multiple timestamped contributions per activity and participant.

Revision ID: 20260815_0047
Revises: 20260814_0046
"""
from alembic import op

revision = "20260815_0047"
down_revision = "20260814_0046"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_logbook_contribution_author",
        "logbook_item_contributions",
        type_="unique",
    )
    op.create_index(
        "idx_logbook_contribution_assignment_item_created",
        "logbook_item_contributions",
        ["assignment_id", "instance_item_id", "created_at"],
    )


def downgrade() -> None:
    # Downgrade is intentionally strict: PostgreSQL will reject it if multiple
    # active/history records already exist for the same participant and activity.
    op.drop_index(
        "idx_logbook_contribution_assignment_item_created",
        table_name="logbook_item_contributions",
    )
    op.create_unique_constraint(
        "uq_logbook_contribution_author",
        "logbook_item_contributions",
        ["instance_item_id", "assignment_id"],
    )
