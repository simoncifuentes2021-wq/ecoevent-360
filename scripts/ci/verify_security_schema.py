from collections import Counter

from sqlalchemy import create_engine, text

from app.core.config import settings
from app.core.database_safety import require_disposable_database


require_disposable_database()
engine = create_engine(settings.migration_database_url or settings.database_url)
critical_tables = {
    "users", "clients", "events", "tasks", "incidents", "evidences", "waste_records",
    "carbon_records", "warehouses", "inventory_items", "stock_balances", "stock_movements",
    "logistics_orders", "logistics_evidences", "purchase_requests", "event_forms",
    "form_responses", "client_portal_configs", "logbook_instances", "logbook_evidences",
    "audit_logs", "reports", "event_session_staff",
}
critical_enums = {"user_role", "event_status", "task_status", "logistics_order_status",
                  "event_form_type", "logbook_instance_status"}
with engine.connect() as connection:
    tables = set(connection.scalars(text("select tablename from pg_tables where schemaname='public'")))
    enums = set(connection.scalars(text("select typname from pg_type where typtype='e'")))
    missing_tables = critical_tables - tables
    missing_enums = critical_enums - enums
    assert not missing_tables, f"Missing critical tables: {sorted(missing_tables)}"
    assert not missing_enums, f"Missing critical enums: {sorted(missing_enums)}"
    hidden_count = connection.scalar(text(
        "select count(*) from information_schema.columns where table_schema='public' "
        "and table_name='events' and column_name='hidden_from_operations'"
    ))
    assert hidden_count == 1, f"hidden_from_operations count={hidden_count}"
    index_count = connection.scalar(text(
        "select count(*) from pg_indexes where schemaname='public' "
        "and indexname='uq_form_responses_form_idempotency'"
    ))
    assert index_count == 1, f"idempotency index count={index_count}"
    policies = list(connection.execute(text(
        "select tablename, policyname from pg_policies where schemaname='public'"
    )))
    duplicates = [item for item, count in Counter(policies).items() if count > 1]
    assert not duplicates, f"Duplicate policies: {duplicates}"
    rls_rows = connection.execute(text(
        "select relname, relrowsecurity from pg_class c join pg_namespace n on n.oid=c.relnamespace "
        "where n.nspname='public' and relname = any(:names)"
    ), {"names": list(critical_tables)})
    rls = {row.relname: row.relrowsecurity for row in rls_rows}
    sensitive = {"users", "clients", "events", "tasks", "evidences", "logistics_orders",
                 "logistics_evidences", "form_responses", "logbook_evidences", "reports",
                 "event_session_staff"}
    without_rls = sorted(name for name in sensitive if not rls.get(name, False))
    assert not without_rls, f"Sensitive tables without RLS: {without_rls}"
    fk_count = connection.scalar(text(
        "select count(*) from pg_constraint where contype='f' and connamespace='public'::regnamespace"
    ))
    assert fk_count >= 40, f"Unexpected foreign-key count: {fk_count}"
print(f"Security schema verified: tables={len(tables)} enums={len(enums)} policies={len(policies)} foreign_keys={fk_count}")
