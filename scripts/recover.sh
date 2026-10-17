#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:5055}"
BASE_URL="${BASE_URL%/}"
POLL_INTERVAL="${POLL_INTERVAL:-1}"
RECOVERY_TIMEOUT="${RECOVERY_TIMEOUT:-30}"
RECOVERY_STABLE_POLLS="${RECOVERY_STABLE_POLLS:-2}"
CURL_MAX_TIME="${CURL_MAX_TIME:-5}"

for command_name in curl jq; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "missing required command: $command_name" >&2
    exit 2
  fi
done

curl --fail-with-body -sS --max-time "$CURL_MAX_TIME" -X POST \
  "${BASE_URL}/demo/state" \
  -H 'Content-Type: application/json' \
  -d '{"mode":"normal"}' >/dev/null

deadline=$((SECONDS + RECOVERY_TIMEOUT))
attempt=1
stable_polls=0
while (( SECONDS <= deadline )); do
  counters='unavailable'
  if health="$(curl --fail-with-body -sS --max-time "$CURL_MAX_TIME" "${BASE_URL}/health" 2>/dev/null)" \
    && counters="$(jq -r '"mode=\(.mode) pool_in_use=\(.pool_in_use)/\(.pool_size) waiting=\(.waiting) submissions=\(.submissions) saturated=\(.pool_saturated)"' <<<"$health" 2>/dev/null)"; then
    if jq -e '(.mode == "normal") and (.journey_status == "ok") and (.pool_in_use == 0) and (.waiting == 0) and (.submissions == 0) and (.pool_saturated == false)' >/dev/null <<<"$health"; then
      stable_polls=$((stable_polls + 1))
    else
      stable_polls=0
    fi
  else
    stable_polls=0
  fi

  printf 'recovery poll %d: %s stable=%d/%d\n' "$attempt" "$counters" "$stable_polls" "$RECOVERY_STABLE_POLLS"
  if (( stable_polls >= RECOVERY_STABLE_POLLS )); then
    printf 'Recuperação confirmada após %d poll(s): %s\n' "$attempt" "$counters"
    exit 0
  fi

  sleep "$POLL_INTERVAL"
  attempt=$((attempt + 1))
done

echo "recovery timeout after ${RECOVERY_TIMEOUT}s" >&2
exit 1
