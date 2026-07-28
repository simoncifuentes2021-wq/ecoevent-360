"""Security stage one: idempotent public form submissions.

Revision ID: 20260727_0037
Revises: 20260725_0036
"""
from alembic import op

revision = "20260727_0037"
down_revision = "20260725_0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "create unique index uq_form_responses_form_idempotency "
        "on form_responses(form_id, ((metadata ->> 'idempotency_key'))) "
        "where metadata ->> 'idempotency_key' is not null"
    )


def downgrade() -> None:
    op.execute("drop index if exists uq_form_responses_form_idempotency")
