#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
PYTHON_BIN="${PYTHON_BIN:-python}"

cd "$BACKEND_DIR"

case "${1:-quick}" in
  quick)
    "$PYTHON_BIN" -m ruff check app tests
    "$PYTHON_BIN" -c "from app.main import app; assert app.openapi()['openapi']; print('FastAPI import and OpenAPI: OK')"
    "$PYTHON_BIN" -c "from sqlalchemy.orm import configure_mappers; import app.models; configure_mappers(); print('SQLAlchemy mappers: OK')"
    ;;
  unit)
    "$PYTHON_BIN" -m pytest tests/test_logbook_rules.py -q
    ;;
  integration)
    "$PYTHON_BIN" -m pytest tests/test_logbook_integration.py tests/test_logbook_certification.py -q
    ;;
  *)
    echo "Usage: $0 {quick|unit|integration}" >&2
    exit 2
    ;;
esac
