#!/usr/bin/env bash
set -euo pipefail

if command -v k6 >/dev/null 2>&1; then
  exec k6 run load/k6.js
fi

if command -v hey >/dev/null 2>&1; then
  exec hey -z 60s -c 8 http://localhost:8080/checkout
fi

echo 'Instale k6 ou hey para gerar carga.' >&2
exit 1
