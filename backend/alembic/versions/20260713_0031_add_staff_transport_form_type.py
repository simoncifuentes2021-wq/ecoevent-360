"""add staff transport form type

Revision ID: 20260713_0031
Revises: 20260712_0030
Create Date: 2026-07-13 03:10:00.000000
"""

from alembic import op


revision = "20260713_0031"
down_revision = "20260712_0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        do $$
        begin
            if not exists (
                select 1
                from pg_enum e
                join pg_type t on t.oid = e.enumtypid
                where t.typname = 'event_form_type'
                  and e.enumlabel = 'STAFF_TRANSPORT_SURVEY'
            ) then
                alter type event_form_type add value 'STAFF_TRANSPORT_SURVEY' after 'TRANSPORT_SURVEY';
            end if;
        end
        $$;
        """
    )


def downgrade() -> None:
    # PostgreSQL does not support dropping enum values safely in-place.
    pass
