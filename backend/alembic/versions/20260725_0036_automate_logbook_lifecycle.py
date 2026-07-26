"""Automate scheduled and overdue logbook lifecycle.

Revision ID: 20260725_0036
Revises: 20260722_0035
"""

from alembic import op

revision = "20260725_0036"
down_revision = "20260722_0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing values originated from ISO instants normalized by the API and are
    # interpreted as UTC during the one-time conversion.
    op.execute(
        "alter table logbook_instances "
        "alter column opens_at type timestamptz using opens_at at time zone 'UTC', "
        "alter column due_at type timestamptz using due_at at time zone 'UTC'"
    )
    op.execute(
        "create index idx_logbook_instances_lifecycle_open "
        "on logbook_instances(opens_at, id) where status = 'SCHEDULED'"
    )
    op.execute(
        "create index idx_logbook_instances_lifecycle_due "
        "on logbook_instances(due_at, id) where status = 'OPEN'"
    )
    op.execute(
        "create unique index uq_audit_logbook_lifecycle_transition "
        "on audit_logs(entity_id, action) "
        "where module = 'logbooks' and action in "
        "('LOGBOOK_LIFECYCLE_OPENED', 'LOGBOOK_LIFECYCLE_OVERDUE')"
    )


def downgrade() -> None:
    op.execute("drop index if exists uq_audit_logbook_lifecycle_transition")
    op.execute("drop index if exists idx_logbook_instances_lifecycle_due")
    op.execute("drop index if exists idx_logbook_instances_lifecycle_open")
    op.execute(
        "alter table logbook_instances "
        "alter column opens_at type timestamp using opens_at at time zone 'UTC', "
        "alter column due_at type timestamp using due_at at time zone 'UTC'"
    )
