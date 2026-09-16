#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://localhost:8080}"

for path in /health /metrics /checkout; do
  body="$(curl --fail-with-body -sS --max-time 5 "${BASE_URL}${path}")"
  printf '%s: %s bytes\n' "$path" "${#body}"
done

echo 'smoke ok'
