"""PostgreSQL-only tenant, supervisor, capability and public-audit regression tests."""

from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text

from app.core.config import settings


@pytest.fixture(scope="module")
def rls_role():
    engine = create_engine(settings.database_url, connect_args={"prepare_threshold": None})
    role = f"docs_rls_{uuid4().hex[:12]}"
    tables = (
        "document_people",
        "document_employments",
        "managed_documents",
        "epp_deliveries",
        "epp_delivery_items",
        "document_signature_requests",
    )
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.exec_driver_sql(f'CREATE ROLE "{role}" NOLOGIN')
        conn.exec_driver_sql(f'GRANT USAGE ON SCHEMA public TO "{role}"')
        for table in tables:
            privilege = "SELECT, UPDATE" if table == "document_signature_requests" else "SELECT"
            conn.exec_driver_sql(f'GRANT {privilege} ON {table} TO "{role}"')
    try:
        yield role
    finally:
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.exec_driver_sql(f'DROP OWNED BY "{role}"')
            conn.exec_driver_sql(f'DROP ROLE "{role}"')
        engine.dispose()


@pytest.fixture
def document_fixture(rls_role):
    engine = create_engine(settings.database_url, connect_args={"prepare_threshold": None})
    with engine.begin() as conn:
        ids = {name: uuid4() for name in (
            "client_a", "client_b", "admin_a", "supervisor_a", "event_a", "event_b",
            "person_a", "person_b", "employment_global_a", "employment_event_a",
            "employment_event_b", "global_doc", "event_doc_a", "event_doc_pair", "event_doc_b",
            "epp_a", "epp_b", "item_a", "item_b", "sig_a", "sig_pair", "sig_b", "sig_expired",
            "sig_revoked", "doc_expired", "doc_revoked",
        )}
        for suffix in ("a", "b"):
            conn.execute(text("insert into clients (id, business_name) values (:id, :name)"), {
                "id": ids[f"client_{suffix}"], "name": f"Documents RLS {suffix} {uuid4()}"
            })
        for name, client_key, role_value in (
            ("admin_a", "client_a", "ADMIN"), ("supervisor_a", "client_a", "SUPERVISOR")
        ):
            conn.execute(text("""insert into users (id, client_id, full_name, email, password_hash, role)
                values (:id, :client_id, :name, :email, 'x', :role)"""), {
                "id": ids[name], "client_id": ids[client_key], "name": name,
                "email": f"{name}-{uuid4()}@example.test", "role": role_value,
            })
        for suffix in ("a", "b"):
            conn.execute(text("""insert into events (id, client_id, name, start_date, end_date, status)
                values (:id, :client_id, :name, :start, :end, 'IN_PROGRESS')"""), {
                "id": ids[f"event_{suffix}"], "client_id": ids[f"client_{suffix}"],
                "name": f"Event {suffix}", "start": datetime.now(UTC).replace(tzinfo=None),
                "end": datetime.now(UTC).replace(tzinfo=None) + timedelta(days=1),
            })
        conn.execute(text("insert into event_staff (event_id, user_id) values (:event_id, :user_id)"), {
            "event_id": ids["event_a"], "user_id": ids["supervisor_a"]
        })
        for suffix in ("a", "b"):
            conn.execute(text("""insert into document_people (id, client_id, first_name, last_name, rut,
                rut_normalized) values (:id, :client_id, :first, 'Worker', :rut, :normalized)"""), {
                "id": ids[f"person_{suffix}"], "client_id": ids[f"client_{suffix}"],
                "first": f"Person {suffix}", "rut": f"11.111.11{suffix}-1",
                "normalized": f"1111111{suffix}1",
            })
        for employment_key, client_key, person_key, event_key in (
            ("employment_global_a", "client_a", "person_a", None),
            ("employment_event_a", "client_a", "person_a", "event_a"),
            # One Greenway person has distinct assignments across client faenas.
            ("employment_event_b", "client_b", "person_a", "event_b"),
        ):
            conn.execute(text("""insert into document_employments
                (id, client_id, person_id, event_id, position)
                values (:id, :client_id, :person_id, :event_id, 'Worker')"""), {
                "id": ids[employment_key], "client_id": ids[client_key],
                "person_id": ids[person_key], "event_id": ids[event_key] if event_key else None,
            })

        docs = (
            ("global_doc", "client_a", "person_a", None),
            ("event_doc_a", "client_a", "person_a", "event_a"),
            ("event_doc_pair", "client_a", "person_a", "event_a"),
            ("event_doc_b", "client_b", "person_a", "event_b"),
            ("doc_expired", "client_a", "person_a", "event_a"),
            ("doc_revoked", "client_a", "person_a", "event_a"),
        )
        for doc_key, client_key, person_key, event_key in docs:
            conn.execute(text("""insert into managed_documents
                (id, client_id, person_id, event_id, created_by, kind, status, title, data, version)
                values (:id, :client_id, :person_id, :event_id, :created_by, 'EPP', 'SENT', :title, '{}'::jsonb, 1)"""), {
                "id": ids[doc_key], "client_id": ids[client_key], "person_id": ids[person_key],
                "event_id": ids[event_key] if event_key else None, "created_by": ids["admin_a"],
                "title": doc_key,
            })
        for suffix in ("a", "b"):
            doc_key, client_key = ("event_doc_a", "client_a") if suffix == "a" else ("event_doc_b", "client_b")
            conn.execute(text("""insert into epp_deliveries (id, client_id, document_id)
                values (:id, :client_id, :document_id)"""), {
                "id": ids[f"epp_{suffix}"], "client_id": ids[client_key], "document_id": ids[doc_key],
            })
            conn.execute(text("""insert into epp_delivery_items
                (id, delivery_id, item_code, label, received_at, received_conformity)
                values (:id, :delivery_id, 'GLOVE', 'Guantes', :received, true)"""), {
                "id": ids[f"item_{suffix}"], "delivery_id": ids[f"epp_{suffix}"], "received": date.today(),
            })
        now = datetime.now(UTC).replace(tzinfo=None)
        token_hashes = {key: uuid4().hex * 2 for key in ("sig_a", "sig_pair", "sig_b", "sig_expired", "sig_revoked")}
        bundle_id = uuid4()
        signatures = (
            ("sig_a", "event_doc_a", now + timedelta(days=2), None, bundle_id),
            ("sig_pair", "event_doc_pair", now + timedelta(days=2), None, bundle_id),
            ("sig_b", "event_doc_b", now + timedelta(days=2), None, None),
            ("sig_expired", "doc_expired", now - timedelta(seconds=1), None, None),
            ("sig_revoked", "doc_revoked", now + timedelta(days=2), now, None),
        )
        for sig_key, doc_key, expires, revoked, assigned_bundle_id in signatures:
            conn.execute(text("""insert into document_signature_requests
                (id, client_id, document_id, token_hash, expires_at, revoked_at, bundle_id)
                values (:id, :client_id, :document_id, :token_hash, :expires, :revoked, :bundle_id)"""), {
                "id": ids[sig_key], "client_id": ids["client_a" if doc_key != "event_doc_b" else "client_b"],
                "document_id": ids[doc_key], "token_hash": token_hashes[sig_key],
                "expires": expires, "revoked": revoked, "bundle_id": assigned_bundle_id,
            })
        yield conn, ids, token_hashes, rls_role
    engine.dispose()


def _context(conn, role: str, *, user_id=None, client_id=None, token_hash=""):
    conn.exec_driver_sql(f'SET LOCAL ROLE "{role}"')
    for key, value in (
        ("app.current_user_id", str(user_id) if user_id else ""),
        ("app.current_role", "ADMIN" if client_id else ""),
        ("app.current_client_id", str(client_id) if client_id else ""),
        ("app.public_document_token_hash", token_hash),
    ):
        conn.execute(text("select set_config(:key, :value, true)"), {"key": key, "value": value})


def test_postgres_document_rls_allows_admin_all_clients_and_scopes_supervisor_and_public(document_fixture):
    conn, ids, tokens, role = document_fixture
    _context(conn, role, user_id=ids["admin_a"], client_id=ids["client_a"])
    assert {
        ids["global_doc"], ids["event_doc_a"], ids["event_doc_b"], ids["doc_expired"], ids["doc_revoked"]
    } <= set(conn.execute(text("select id from managed_documents")).scalars())
    assert {ids["person_a"], ids["person_b"]} <= set(
        conn.execute(text("select id from document_people")).scalars()
    )
    assert {
        ids["employment_global_a"], ids["employment_event_a"], ids["employment_event_b"]
    } <= set(conn.execute(text("select id from document_employments")).scalars())
    assert {ids["event_doc_a"], ids["event_doc_b"]} <= set(
        conn.execute(text("select document_id from epp_deliveries")).scalars()
    )
    assert {ids["item_a"], ids["item_b"]} <= set(
        conn.execute(text("select id from epp_delivery_items")).scalars()
    )

    conn.exec_driver_sql("RESET ROLE")
    _context(conn, role, user_id=ids["supervisor_a"])
    conn.execute(text("select set_config('app.current_role', 'SUPERVISOR', true)"))
    assert set(conn.execute(text("select id from managed_documents")).scalars()) == {
        ids["event_doc_a"], ids["event_doc_pair"], ids["doc_expired"], ids["doc_revoked"]
    }
    assert conn.execute(text("select id from managed_documents where id=:id"), {"id": ids["global_doc"]}).first() is None
    assert conn.execute(text("select id from managed_documents where id=:id"), {"id": ids["event_doc_b"]}).first() is None
    assert conn.execute(text("select id from document_people where id=:id"), {"id": ids["person_b"]}).first() is None
    assert set(conn.execute(text("select id from document_employments")).scalars()) == {ids["employment_event_a"]}
    assert conn.execute(text("select id from epp_delivery_items where id=:id"), {"id": ids["item_b"]}).first() is None

    conn.exec_driver_sql("RESET ROLE")
    _context(conn, role, token_hash=tokens["sig_a"])
    assert set(conn.execute(text("select id from managed_documents")).scalars()) == {
        ids["event_doc_a"], ids["event_doc_pair"]
    }
    assert conn.execute(text("select id from document_people")).scalars().all() == [ids["person_a"]]
    assert conn.execute(text("select id from document_employments")).scalars().all() == []
    assert conn.execute(text("select document_id from epp_deliveries")).scalars().all() == [ids["event_doc_a"]]
    assert conn.execute(text("select id from epp_delivery_items")).scalars().all() == [ids["item_a"]]
    assert set(conn.execute(text("select id from document_signature_requests")).scalars()) == {
        ids["sig_a"], ids["sig_pair"]
    }
    updated = conn.execute(text("update document_signature_requests set worker_signed_name='tamper' where id=:id"), {"id": ids["sig_b"]})
    assert updated.rowcount == 0
    paired_update = conn.execute(
        text("update document_signature_requests set opened_at=now() where id=:id"),
        {"id": ids["sig_pair"]},
    )
    assert paired_update.rowcount == 1
    conn.execute(text("update document_signature_requests set opened_at=now() where id=:id"), {"id": ids["sig_a"]})
    conn.execute(text("select app_record_public_document_audit(:id, 'DOCUMENT_PUBLIC_OPENED')"), {"id": ids["event_doc_a"]})
    conn.execute(text("update document_signature_requests set worker_signed_at=now(), worker_signed_name='Person A Worker' where id=:id"), {"id": ids["sig_a"]})
    conn.execute(text("select app_record_public_document_audit(:id, 'DOCUMENT_WORKER_SIGNED')"), {"id": ids["event_doc_a"]})
    conn.exec_driver_sql("RESET ROLE")
    audit = conn.execute(text("select action, metadata from audit_logs where entity_id=:id and action in ('DOCUMENT_PUBLIC_OPENED','DOCUMENT_WORKER_SIGNED') order by action"), {"id": ids["event_doc_a"]}).all()
    assert {row.action for row in audit} == {"DOCUMENT_PUBLIC_OPENED", "DOCUMENT_WORKER_SIGNED"}
    assert all(row.metadata == {"source": "public_portal"} for row in audit)

    _context(conn, role, token_hash=tokens["sig_expired"])
    assert conn.execute(text("select id from managed_documents")).scalars().all() == []
    conn.exec_driver_sql("RESET ROLE")
    _context(conn, role, token_hash=tokens["sig_revoked"])
    assert conn.execute(text("select id from managed_documents")).scalars().all() == []
