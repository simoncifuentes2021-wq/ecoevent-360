#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
PYTHON_BIN="${PYTHON_BIN:-python}"

: "${DATABASE_URL:?DATABASE_URL must point to an isolated PostgreSQL test database}"
: "${CI_DATABASE_CONFIRM:?Set CI_DATABASE_CONFIRM=ecoevent-test-only to initialize the test database}"

if [[ "$CI_DATABASE_CONFIRM" != "ecoevent-test-only" ]]; then
  echo "Refusing database initialization without the exact test-only confirmation." >&2
  exit 2
fi

case "$DATABASE_URL" in
  *localhost*|*127.0.0.1*|*postgres:5432*|*postgresql:5432*) ;;
  *)
    echo "Refusing to initialize a database that is not explicitly local or the CI postgres service." >&2
    exit 2
    ;;
esac

cd "$BACKEND_DIR"
"$PYTHON_BIN" -c 'import os; from psycopg.conninfo import conninfo_to_dict; name = conninfo_to_dict(os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")).get("dbname", ""); assert "test" in name.lower() or "_ci" in name.lower(), f"Refusing non-test database: {name}"'
"$PYTHON_BIN" "$ROOT_DIR/scripts/ci/wait_for_postgres.py"
"$PYTHON_BIN" -c 'from app.core.database_safety import require_disposable_database; print(require_disposable_database())'
"$PYTHON_BIN" -m alembic upgrade head
"$PYTHON_BIN" "$ROOT_DIR/scripts/ci/verify_alembic_head.py"
"$PYTHON_BIN" "$ROOT_DIR/scripts/ci/verify_security_schema.py"
