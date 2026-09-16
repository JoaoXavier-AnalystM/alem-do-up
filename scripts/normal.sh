#!/usr/bin/env bash
set -euo pipefail

curl --fail-with-body -sS -X POST \
  http://localhost:8080/demo/state \
  -H 'Content-Type: application/json' \
  -d '{"mode":"normal"}'
printf '\nEstado normal: pool livre, checkout rápido, /health 200\n'
