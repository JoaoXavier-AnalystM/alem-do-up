#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://localhost:5055}"

for path in /health /metrics /checkout; do
  success=0
  for attempt in $(seq 1 30); do
    if body="$(curl --fail-with-body -sS --max-time 5 "${BASE_URL}${path}" 2>/dev/null)"; then
      printf '%s: %s bytes\n' "$path" "${#body}"
      success=1
      break
    fi
    sleep 2
  done
  if [ "$success" -ne 1 ]; then
    echo "smoke failed: ${BASE_URL}${path}" >&2
    exit 1
  fi
done

echo 'smoke ok'
