#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR/frontend"

case "${1:-quick}" in
  quick)
    npm run verify:quick
    ;;
  logbooks)
    npm run test:logbooks
    ;;
  build)
    npm run build
    ;;
  *)
    echo "Usage: $0 {quick|logbooks|build}" >&2
    exit 2
    ;;
esac
