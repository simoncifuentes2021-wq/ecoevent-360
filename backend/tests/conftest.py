"""Global safety guard: integration tests may only use an explicitly disposable DB."""
import os

import pytest


def pytest_sessionstart(session):
    if os.getenv("CI_DATABASE_CONFIRM") not in {"ecoevent-test-only", "local-disposable-test"}:
        pytest.exit(
            "Refusing DB tests: set CI_DATABASE_CONFIRM only for an isolated disposable database",
            returncode=5,
        )
