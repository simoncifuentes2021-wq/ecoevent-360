#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
bash "$ROOT_DIR/scripts/ci/backend.sh" quick
bash "$ROOT_DIR/scripts/ci/backend.sh" unit
bash "$ROOT_DIR/scripts/ci/bootstrap-test-database.sh"
bash "$ROOT_DIR/scripts/ci/backend.sh" integration
bash "$ROOT_DIR/scripts/ci/frontend.sh" quick
bash "$ROOT_DIR/scripts/ci/frontend.sh" build
"${PYTHON_BIN:-python}" "$ROOT_DIR/scripts/ci/validate-workflow.py"
git -C "$ROOT_DIR" diff --check
