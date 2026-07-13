"""fix login rls for users

Revision ID: 20260713_0033
Revises: 20260713_0032
Create Date: 2026-07-13 04:30:00.000000
"""

from alembic import op


revision = "20260713_0033"
down_revision = "20260713_0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        drop policy if exists users_read_rls on users;
        drop policy if exists users_self_update_rls on users;

        create policy users_read_rls on users
            for select
            using (
                app_current_user_id() is null
                or app_is_admin()
                or id = app_current_user_id()
                or (
                    app_current_role() = 'SUPERVISOR'
                    and role in ('SUPERVISOR', 'WORKER', 'LOGISTICS_OPERATOR')
                    and is_active = true
                )
            );

        create policy users_self_update_rls on users
            for update
            using (id = app_current_user_id())
            with check (id = app_current_user_id());
        """
    )


def downgrade() -> None:
    op.execute(
        """
        drop policy if exists users_self_update_rls on users;
        drop policy if exists users_read_rls on users;

        create policy users_read_rls on users
            for select
            using (
                app_is_admin()
                or id = app_current_user_id()
                or (
                    app_current_role() = 'SUPERVISOR'
                    and role in ('SUPERVISOR', 'WORKER', 'LOGISTICS_OPERATOR')
                    and is_active = true
                )
            );
        """
    )
