#!/usr/bin/env bash
# Run unit and integration tests for Book-IA.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> Book-IA test suite"
echo "    Root: $ROOT"

if command -v docker >/dev/null 2>&1; then
  if [ -f docker-compose.test.yml ]; then
    echo "==> Optional: docker compose -f docker-compose.test.yml up -d (postgres:5433, redis:6380)"
  fi
fi

PYTHON="${PYTHON:-python}"
if ! command -v "$PYTHON" >/dev/null 2>&1; then
  PYTHON=python3
fi

echo "==> Unit tests (tests/ excluding test_integration)"
"$PYTHON" -m pytest tests \
  --ignore=tests/test_integration \
  -v \
  "$@"

echo "==> Integration tests (tests/test_integration)"
"$PYTHON" -m pytest tests/test_integration -v --cov-fail-under=0 "$@"

echo "==> All tests passed."
