#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:5055}"
BASE_URL="${BASE_URL%/}"
POLL_INTERVAL="${POLL_INTERVAL:-1}"
INCIDENT_TIMEOUT="${INCIDENT_TIMEOUT:-30}"
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
  -d '{"mode":"incident"}')"

if ! jq -e '.mode == "incident" and .health.mode == "incident"' >/dev/null <<<"$state_response"; then
  echo 'incident activation returned unexpected state' >&2
  exit 1
fi

deadline=$((SECONDS + INCIDENT_TIMEOUT))
attempt=1
while (( SECONDS <= deadline )); do
  if health="$(curl --fail-with-body -sS --max-time "$CURL_MAX_TIME" "${BASE_URL}/health" 2>/dev/null)" \
    && jq -e '(.mode == "incident") and (.pool_saturated == true) and (.pool_in_use >= .pool_size)' >/dev/null <<<"$health"; then
    counters="$(jq -r '"mode=\(.mode) pool_in_use=\(.pool_in_use)/\(.pool_size) waiting=\(.waiting) saturated=\(.pool_saturated)"' <<<"$health")"
    printf 'Incidente ativado: saturação confirmada após %d tentativa(s): %s\n' "$attempt" "$counters"
    exit 0
  fi

  sleep "$POLL_INTERVAL"
  attempt=$((attempt + 1))
done

echo "incident saturation timeout after ${INCIDENT_TIMEOUT}s" >&2
exit 1
