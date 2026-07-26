#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
bash "$ROOT_DIR/scripts/ci/backend.sh" unit
bash "$ROOT_DIR/scripts/ci/backend.sh" integration
bash "$ROOT_DIR/scripts/ci/frontend.sh" logbooks
