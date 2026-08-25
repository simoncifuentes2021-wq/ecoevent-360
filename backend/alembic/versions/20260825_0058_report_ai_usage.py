"""Track report AI usage, costs and application state.

Revision ID: 20260825_0058
Revises: 20260824_0057
"""

from alembic import op
import sqlalchemy as sa

revision = "20260825_0058"
down_revision = "20260824_0057"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for name in ("input_tokens", "output_tokens", "cached_input_tokens", "total_tokens", "attempt_count"):
        op.add_column("ai_generations", sa.Column(name, sa.Integer(), nullable=False, server_default="0"))
    op.add_column("ai_generations", sa.Column("estimated_cost_usd", sa.Numeric(12, 8)))
    op.add_column("ai_generations", sa.Column("actual_cost_usd", sa.Numeric(12, 8)))
    op.add_column("ai_generations", sa.Column("provider_request_id", sa.String(180)))
    op.add_column("ai_generations", sa.Column("applied", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.drop_constraint("ck_ai_generations_status", "ai_generations", type_="check")
    op.create_check_constraint("ck_ai_generations_status", "ai_generations", "status in ('PENDING','SUCCEEDED','FAILED','STALE')")


def downgrade() -> None:
    op.drop_constraint("ck_ai_generations_status", "ai_generations", type_="check")
    op.create_check_constraint("ck_ai_generations_status", "ai_generations", "status in ('PENDING','SUCCEEDED','FAILED')")
    for name in ("applied", "provider_request_id", "actual_cost_usd", "estimated_cost_usd", "attempt_count", "total_tokens", "cached_input_tokens", "output_tokens", "input_tokens"):
        op.drop_column("ai_generations", name)
