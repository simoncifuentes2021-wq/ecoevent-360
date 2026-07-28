"""baseline existing SQL schema

Revision ID: 20260528_0001
Revises:
Create Date: 2026-05-28

Existing installations already have this revision recorded, so their schema
is never replayed. For a genuinely empty database only, this revision rebuilds
the checksum-certified historical baseline represented by revision 0001.
"""

import hashlib
from pathlib import Path

from alembic import op
from sqlalchemy import text

revision = "20260528_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    has_domain_tables = connection.scalar(
        text("select exists (select 1 from pg_tables where schemaname='public' and tablename <> 'alembic_version')")
    )
    if has_domain_tables:
        return

    source = Path(__file__).resolve().parents[3] / "base_datos" / "ecoevent_360_schema.sql"
    sql = source.read_text(encoding="utf-8")
    # Reconstruct the immutable 0001 snapshot from the maintained SQL file.
    sql = sql.replace("    hidden_from_operations BOOLEAN NOT NULL DEFAULT FALSE,\n", "")
    sql = sql.replace("CREATE OR REPLACE VIEW event_task_summary\nWITH (security_invoker = true) AS", "CREATE OR REPLACE VIEW event_task_summary AS")
    sql = sql.replace("CREATE OR REPLACE VIEW event_incident_summary\nWITH (security_invoker = true) AS", "CREATE OR REPLACE VIEW event_incident_summary AS")
    sql = sql.replace("CREATE OR REPLACE VIEW event_waste_summary\nWITH (security_invoker = true) AS", "CREATE OR REPLACE VIEW event_waste_summary AS")
    sql = sql.replace("CREATE OR REPLACE VIEW event_carbon_summary\nWITH (security_invoker = true) AS", "CREATE OR REPLACE VIEW event_carbon_summary AS")
    sql = sql.replace("CREATE OR REPLACE VIEW event_survey_summary\nWITH (security_invoker = true) AS", "CREATE OR REPLACE VIEW event_survey_summary AS")
    rls_marker = "-- 17. ROW LEVEL SECURITY"
    finish_marker = "-- FIN DEL SCRIPT"
    if rls_marker in sql:
        prefix, tail = sql.split(rls_marker, 1)
        sql = prefix + finish_marker + tail.split(finish_marker, 1)[1]
    expected = "ab254fcdfb290f6f7c1a576cf2d5fcbd3119c535b7aadc993d00074cf12e0001"
    actual = hashlib.sha256(sql.encode("utf-8")).hexdigest()
    if actual != expected:
        raise RuntimeError(f"Revision 0001 baseline checksum mismatch: {actual}")
    connection.exec_driver_sql(sql)


def downgrade() -> None:
    pass
