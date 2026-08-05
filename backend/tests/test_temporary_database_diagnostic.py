from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_active_user
from app.api.routers import temporary_database_diagnostic as diagnostic
from app.core.config import settings
from app.db.session import get_db
from app.main import app
from app.models.enums import UserRole


IDENTITY = {
    "current_user": "runtime_client",
    "current_database": "app_database",
    "rolsuper": False,
    "rolcreatedb": False,
    "rolcreaterole": False,
    "rolinherit": True,
    "rolreplication": False,
    "rolbypassrls": False,
}


class FakeResult:
    def one(self):
        return SimpleNamespace(_mapping=IDENTITY)


class FakeSession:
    def execute(self, _query):
        return FakeResult()


class FakeConnection(FakeSession):
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None


class FakeEngine:
    disposed = False

    def connect(self):
        return FakeConnection()

    def dispose(self):
        self.disposed = True


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = lambda: FakeSession()
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def authorize(role: UserRole) -> None:
    app.dependency_overrides[get_current_active_user] = lambda: SimpleNamespace(
        role=role,
        is_active=True,
    )


def test_super_admin_can_run_runtime_diagnostic_without_migration(client, monkeypatch):
    authorize(UserRole.SUPER_ADMIN)
    monkeypatch.setattr(settings, "migration_database_url", None)

    response = client.get("/api/v1/internal/temporary/database-identity")

    assert response.status_code == 200
    assert response.json() == {
        "runtime": IDENTITY,
        "migration_configured": False,
        "distinct_configuration": False,
        "migration": None,
    }


def test_super_admin_can_compare_configured_migration_identity(client, monkeypatch):
    authorize(UserRole.SUPER_ADMIN)
    monkeypatch.setattr(settings, "migration_database_url", "postgresql://migration.invalid/db")
    engine = FakeEngine()
    monkeypatch.setattr(diagnostic, "_migration_engine", lambda: engine)

    response = client.get("/api/v1/internal/temporary/database-identity")

    assert response.status_code == 200
    assert response.json()["migration"] == IDENTITY
    assert response.json()["migration_configured"] is True
    assert response.json()["distinct_configuration"] is True
    assert engine.disposed is True


def test_unauthenticated_user_is_rejected(client):
    response = client.get("/api/v1/internal/temporary/database-identity")
    assert response.status_code in {401, 403}


@pytest.mark.parametrize(
    "role",
    [
        UserRole.ADMIN,
        UserRole.SUPERVISOR,
        UserRole.WORKER,
        UserRole.LOGISTICS_OPERATOR,
        UserRole.CLIENT,
    ],
)
def test_every_non_super_admin_role_is_rejected(client, role):
    authorize(role)
    response = client.get("/api/v1/internal/temporary/database-identity")
    assert response.status_code == 403
    assert response.json() == {"detail": "Insufficient role"}


def test_response_contains_only_allowlisted_non_secret_fields(client, monkeypatch):
    authorize(UserRole.SUPER_ADMIN)
    monkeypatch.setattr(settings, "migration_database_url", None)

    payload = client.get("/api/v1/internal/temporary/database-identity").json()
    serialized = str(payload).lower()

    assert set(payload) == {
        "runtime",
        "migration_configured",
        "distinct_configuration",
        "migration",
    }
    assert set(payload["runtime"]) == set(IDENTITY)
    for forbidden in ("url", "host", "port", "password", "token", "secret", "key"):
        assert forbidden not in serialized


def test_connection_error_returns_sanitized_message(client, monkeypatch):
    authorize(UserRole.SUPER_ADMIN)
    monkeypatch.setattr(settings, "migration_database_url", None)
    monkeypatch.setattr(
        diagnostic,
        "_identity",
        lambda _connection: (_ for _ in ()).throw(
            RuntimeError("postgresql://user:password@private-host/database")
        ),
    )

    response = client.get("/api/v1/internal/temporary/database-identity")

    assert response.status_code == 503
    assert response.json() == {"detail": "Database identity diagnostic unavailable"}
    assert "password" not in response.text
    assert "private-host" not in response.text
