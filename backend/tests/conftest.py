"""Global safety guard: integration tests may only use an explicitly disposable DB."""
import pytest

from app.core.database_safety import require_disposable_database


def pytest_sessionstart(session):
    try:
        identity = require_disposable_database()
    except RuntimeError as exc:
        pytest.exit(
            f"Refusing DB tests: {exc}",
            returncode=5,
        )
    print(
        "Disposable PostgreSQL confirmed: "
        f"host={identity['host']} database={identity['database']} "
        f"runtime_user={identity['runtime_user']} migration_user={identity['migration_user']} "
        "CI_DATABASE_CONFIRM=active supabase=absent"
    )
