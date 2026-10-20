"""Allow ADMIN and SUPER_ADMIN across clients in the Documents module.

Revision ID: 20261006_0078
Revises: 20261006_0077
"""

from collections.abc import Sequence

from alembic import op


revision: str = "20261006_0078"
down_revision: str | None = "20261006_0077"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_GLOBAL_ADMIN_SCOPE = """
    create or replace function app_documents_can_access_client(target_client_id uuid)
    returns boolean language sql stable security definer set search_path = public as $$
        select app_current_role() in ('SUPER_ADMIN', 'ADMIN')
    $$
"""

_CLIENT_SCOPED_ADMIN = """
    create or replace function app_documents_can_access_client(target_client_id uuid)
    returns boolean language sql stable security definer set search_path = public as $$
        select app_current_role() = 'SUPER_ADMIN'
            or (app_current_role() = 'ADMIN'
                and app_current_client_id() = target_client_id)
    $$
"""


def upgrade() -> None:
    op.execute(_GLOBAL_ADMIN_SCOPE)


def downgrade() -> None:
    op.execute(_CLIENT_SCOPED_ADMIN)
