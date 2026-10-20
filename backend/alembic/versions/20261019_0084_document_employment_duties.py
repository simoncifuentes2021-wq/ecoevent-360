"""Store contract duties separately from a worker's position."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20261019_0084"
down_revision: str | None = "20261019_0083"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("document_employments", sa.Column("duties", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("document_employments", "duties")
