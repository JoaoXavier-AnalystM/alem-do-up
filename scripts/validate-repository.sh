#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if command -v uv >/dev/null 2>&1; then
  uv run --no-cache --with pytest --with pyyaml pytest tests/test_repository_contracts.py -q
elif command -v python3 >/dev/null 2>&1; then
  python3 -m pytest tests/test_repository_contracts.py -q
else
  echo 'QA requires uv or python3 with pytest and PyYAML.' >&2
  exit 1
fi

if command -v docker >/dev/null 2>&1; then
  docker compose --env-file "$ROOT_DIR/.env.example" config --quiet
  docker compose --env-file "$ROOT_DIR/opendockwatch/.env.example" \
    -f "$ROOT_DIR/opendockwatch/docker-compose.yml" config --quiet
  docker compose --env-file "$ROOT_DIR/cloudflare/.env.example" \
    -f "$ROOT_DIR/cloudflare/docker-compose.yml" config --quiet
  echo 'Docker Compose contracts: OK'
else
  echo 'Docker unavailable: skipped Compose validation; static contracts passed.'
fi
