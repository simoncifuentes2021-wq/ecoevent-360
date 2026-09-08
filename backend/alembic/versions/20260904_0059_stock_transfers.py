"""Add stock transfer movement types.

Revision ID: 20260904_0059
Revises: 20260825_0058
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260904_0059"
down_revision: str | None = "20260825_0058"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _add_enum_value(value: str) -> None:
    op.execute(
        f"""
        do $$
        begin
            if not exists (
                select 1
                from pg_enum e
                join pg_type t on t.oid = e.enumtypid
                where t.typname = 'stock_movement_type'
                  and e.enumlabel = '{value}'
            ) then
                alter type stock_movement_type add value '{value}';
            end if;
        end $$;
        """
    )


def upgrade() -> None:
    _add_enum_value("TRANSFER_OUT")
    _add_enum_value("TRANSFER_IN")


def downgrade() -> None:
    # PostgreSQL enum values cannot be removed safely while rows may reference them.
    pass
