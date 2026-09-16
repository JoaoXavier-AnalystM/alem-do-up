#!/usr/bin/env bash
set -euo pipefail

curl --fail-with-body -sS -X POST \
  http://localhost:5055/demo/state \
  -H 'Content-Type: application/json' \
  -d '{"mode":"incident"}'

for _ in 1 2 3 4 5; do
  curl --fail-with-body -sS -X POST http://localhost:5055/demo/hold >/dev/null &
done

printf '\nIncidente ativado: conexões ocupadas. Abra Grafana e rode scripts/load.sh.\n'
