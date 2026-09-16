#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Criado opendockwatch/.env a partir de .env.example."
fi

if ! grep -Eq '^AUTH_USER=.+$' .env || ! grep -Eq '^AUTH_PASS_HASH=.+$' .env || ! grep -Eq '^SESSION_SECRET=.+$' .env; then
  echo "Configure AUTH_USER, AUTH_PASS_HASH e SESSION_SECRET em opendockwatch/.env antes de iniciar." >&2
  exit 1
fi

mkdir -p data
if [ ! -f config/hosts.json ]; then
  cp config/hosts.example.json config/hosts.json
elif grep -q '"hosts"' config/hosts.json; then
  cp config/hosts.json config/hosts.json.invalid-format.bak
  cp config/hosts.example.json config/hosts.json
  echo "Formato antigo de config/hosts.json corrigido; backup salvo em config/hosts.json.invalid-format.bak."
fi

docker compose pull
docker compose up -d --remove-orphans
docker compose ps

echo "OpenDockWatch: http://localhost:${OPENDOCKWATCH_PORT:-3001}"
