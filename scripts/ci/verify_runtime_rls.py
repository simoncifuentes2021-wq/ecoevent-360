from uuid import UUID

from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from app.core.database_safety import require_disposable_database


identity = require_disposable_database()
assert identity["runtime_user"] != identity["migration_user"], "Runtime and migrator roles must differ"
from app.core.config import settings  # noqa: E402

owner = create_engine(settings.migration_database_url)
runtime = create_engine(settings.database_url, pool_size=1, max_overflow=0)
ids = {name: UUID(f"00000000-0000-0000-0001-{number:012d}") for number, name in enumerate((
    "client_a", "client_b", "client_a_user", "client_b_user", "supervisor_assigned",
    "supervisor_other", "worker_assigned", "worker_other", "operator_assigned",
    "operator_other", "inactive", "event_a", "event_b", "warehouse_a", "warehouse_b",
    "order_a", "order_b", "staff_supervisor", "staff_worker", "warehouse_user",
), 1)}


def set_context(connection, user, role, client=None):
    connection.execute(text("select set_config('app.current_user_id', :v, true)"), {"v": str(user)})
    connection.execute(text("select set_config('app.current_role', :v, true)"), {"v": role})
    connection.execute(text("select set_config('app.current_client_id', :v, true)"), {"v": str(client or "")})


def visible(connection, table):
    return connection.scalar(text(f"select count(*) from {table}"))


with owner.begin() as connection:
    connection.execute(text("insert into clients(id,business_name) values (:client_a,'RLS Client A'),(:client_b,'RLS Client B')"), ids)
    users = [
        ("client_a_user", "CLIENT", "client_a", True), ("client_b_user", "CLIENT", "client_b", True),
        ("supervisor_assigned", "SUPERVISOR", None, True), ("supervisor_other", "SUPERVISOR", None, True),
        ("worker_assigned", "WORKER", None, True), ("worker_other", "WORKER", None, True),
        ("operator_assigned", "LOGISTICS_OPERATOR", None, True), ("operator_other", "LOGISTICS_OPERATOR", None, True),
        ("inactive", "WORKER", None, False),
    ]
    for key, role, client, active in users:
        connection.execute(text("insert into users(id,client_id,full_name,email,password_hash,role,is_active) values (:id,:client,:name,:email,'x',:role,:active)"),
                           {"id": ids[key], "client": ids[client] if client else None, "name": key,
                            "email": f"rls-{key}@example.invalid", "role": role, "active": active})
    connection.execute(text("insert into events(id,client_id,name,start_date,end_date,status) values (:event_a,:client_a,'RLS Event A',now(),now()+interval '1 day','IN_PROGRESS'),(:event_b,:client_b,'RLS Event B',now(),now()+interval '1 day','IN_PROGRESS')"), ids)
    connection.execute(text("insert into event_staff(id,event_id,user_id) values (:staff_supervisor,:event_a,:supervisor_assigned),(:staff_worker,:event_a,:worker_assigned)"), ids)
    connection.execute(text("insert into warehouses(id,name) values (:warehouse_a,'RLS Warehouse A'),(:warehouse_b,'RLS Warehouse B')"), ids)
    connection.execute(text("insert into warehouse_users(id,warehouse_id,user_id,can_view_stock) values (:warehouse_user,:warehouse_a,:operator_assigned,true)"), ids)
    connection.execute(text("insert into logistics_orders(id,event_id,warehouse_id,requested_by,assigned_operator_id,title) values (:order_a,:event_a,:warehouse_a,:supervisor_assigned,:operator_assigned,'RLS Order A'),(:order_b,:event_b,:warehouse_b,:supervisor_other,:operator_other,'RLS Order B')"), ids)

try:
    cases = [
        ("client_a_user", "CLIENT", "client_a", 1), ("client_b_user", "CLIENT", "client_b", 1),
        ("supervisor_assigned", "SUPERVISOR", None, 1), ("supervisor_other", "SUPERVISOR", None, 0),
        ("worker_assigned", "WORKER", None, 1), ("worker_other", "WORKER", None, 0),
    ]
    for user, role, client, expected in cases:
        with runtime.begin() as connection:
            set_context(connection, ids[user], role, ids[client] if client else None)
            assert visible(connection, "events") == expected, f"event isolation failed for {user}"
    with runtime.begin() as connection:
        set_context(connection, ids["operator_assigned"], "LOGISTICS_OPERATOR")
        assert visible(connection, "logistics_orders") == 1
        assert visible(connection, "warehouses") == 1
    with runtime.begin() as connection:
        set_context(connection, ids["operator_other"], "LOGISTICS_OPERATOR")
        assert visible(connection, "logistics_orders") == 1
        assert visible(connection, "warehouses") == 0
    with runtime.connect() as connection:
        transaction = connection.begin()
        set_context(connection, ids["client_a_user"], "CLIENT", ids["client_a"])
        assert connection.scalar(text("select current_setting('app.current_user_id', true)")) == str(ids["client_a_user"])
        transaction.rollback()
        with connection.begin():
            assert connection.scalar(text("select current_setting('app.current_user_id', true)")) in (None, "")
            assert visible(connection, "events") == 0
    try:
        with runtime.begin() as connection:
            connection.execute(text("create table rls_forbidden_test(id integer)"))
        raise AssertionError("Runtime role unexpectedly created a table")
    except DBAPIError:
        pass
finally:
    with owner.begin() as connection:
        connection.execute(text("delete from clients where id in (:a,:b)"), {"a": ids["client_a"], "b": ids["client_b"]})
        connection.execute(text("delete from warehouses where id in (:a,:b)"), {"a": ids["warehouse_a"], "b": ids["warehouse_b"]})
        connection.execute(text("delete from users where email like 'rls-%@example.invalid'"))

print("Runtime RLS verified: clients, supervisors, workers, logistics operators, SET LOCAL cleanup, pooled connection reuse, DDL denied")
