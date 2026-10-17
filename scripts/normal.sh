#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:5055}"
BASE_URL="${BASE_URL%/}"
CURL_MAX_TIME="${CURL_MAX_TIME:-5}"

for command_name in curl jq; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "missing required command: $command_name" >&2
    exit 2
  fi
done

state_response="$(curl --fail-with-body -sS --max-time "$CURL_MAX_TIME" -X POST \
  "${BASE_URL}/demo/state" \
  -H 'Content-Type: application/json' \
  -d '{"mode":"normal"}')"

if ! jq -e '.mode == "normal" and .health.mode == "normal" and .health.pool_in_use == 0 and .health.waiting == 0 and .health.pool_saturated == false' >/dev/null <<<"$state_response"; then
  echo 'normal activation returned unexpected state' >&2
  exit 1
fi

printf 'Estado normal confirmado: pool_in_use=0 waiting=0 saturated=false\n'
