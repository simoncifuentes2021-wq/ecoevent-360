"""Persist the worker-completed EPP/RIOHS/EIRL acknowledgments.

Revision ID: 20261006_0080
Revises: 20261006_0079
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20261006_0080"
down_revision: str | None = "20261006_0079"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "document_signature_requests",
        sa.Column("worker_form_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("document_signature_requests", "worker_form_data")
