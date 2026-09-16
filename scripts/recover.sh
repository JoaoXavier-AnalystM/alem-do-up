#!/usr/bin/env bash
set -euo pipefail

curl --fail-with-body -sS -X POST \
  http://localhost:8080/demo/state \
  -H 'Content-Type: application/json' \
  -d '{"mode":"normal"}'
printf '\nRecuperação acionada: observe os gráficos até o pool esvaziar.\n'
