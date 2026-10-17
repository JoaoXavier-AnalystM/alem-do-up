#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-${BASE_URL:-http://localhost:5055}}"
BASE_URL="${BASE_URL%/}"
SMOKE_ATTEMPTS="${SMOKE_ATTEMPTS:-30}"
SMOKE_INTERVAL="${SMOKE_INTERVAL:-2}"
CURL_MAX_TIME="${CURL_MAX_TIME:-5}"

for command_name in curl jq; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "missing required command: $command_name" >&2
    exit 2
  fi
done

check_health() {
  jq -e '(.http_status == 200) and (.status == "ok") and (.journey_status == "ok") and (.mode == "normal") and (.pool_saturated == false) and (.pool_in_use == 0) and (.waiting == 0)' >/dev/null <<<"$1"
}

check_metrics() {
  grep -q '^# HELP checkout_http_requests_total' <<<"$1" \
    && grep -q '^# HELP checkout_db_pool_in_use' <<<"$1" \
    && grep -q '^# HELP checkout_db_pool_waiting' <<<"$1"
}

check_checkout() {
  jq -e '(.status == "confirmed") and (.mode == "normal")' >/dev/null <<<"$1"
}

check_endpoint() {
  local path="$1"
  local validator="$2"
  local attempt=1
  local body

  while (( attempt <= SMOKE_ATTEMPTS )); do
    if body="$(curl --fail-with-body -sS --max-time "$CURL_MAX_TIME" "${BASE_URL}${path}" 2>/dev/null)" \
      && "$validator" "$body"; then
      printf '%s: %d bytes, contrato confirmado\n' "$path" "${#body}"
      return 0
    fi
    sleep "$SMOKE_INTERVAL"
    attempt=$((attempt + 1))
  done

  echo "smoke failed: ${BASE_URL}${path} after ${SMOKE_ATTEMPTS} attempts" >&2
  return 1
}

check_endpoint /health check_health
check_endpoint /metrics check_metrics
check_endpoint /checkout check_checkout
echo 'smoke ok: health normal, metrics presentes, checkout confirmado'
