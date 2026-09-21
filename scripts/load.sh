#!/usr/bin/env bash
set -euo pipefail
BASE_URL="${BASE_URL:-http://localhost:5055}"
PROMETHEUS_RW_URL="${PROMETHEUS_RW_URL:-http://localhost:9090/api/v1/write}"
PROMETHEUS_RW_TREND_STATS="${PROMETHEUS_RW_TREND_STATS:-p(50),p(90),p(95),avg,min,max}"
K6_VUS="${K6_VUS:-8}"
K6_DURATION="${K6_DURATION:-60s}"
K6_TEST_ID="${K6_TEST_ID:-checkout-load}"
K6_INCIDENT="${K6_INCIDENT:-false}"

if command -v k6 >/dev/null 2>&1; then
  exec env BASE_URL="$BASE_URL" K6_VUS="$K6_VUS" K6_DURATION="$K6_DURATION" K6_TEST_ID="$K6_TEST_ID" K6_INCIDENT="$K6_INCIDENT" K6_PROMETHEUS_RW_SERVER_URL="$PROMETHEUS_RW_URL" K6_PROMETHEUS_RW_TREND_STATS="$PROMETHEUS_RW_TREND_STATS" k6 run -o experimental-prometheus-rw load/k6.js
fi

if command -v docker >/dev/null 2>&1; then
  exec docker run --rm --network host -e BASE_URL="$BASE_URL" -e K6_VUS="$K6_VUS" -e K6_DURATION="$K6_DURATION" -e K6_TEST_ID="$K6_TEST_ID" -e K6_INCIDENT="$K6_INCIDENT" -e K6_PROMETHEUS_RW_SERVER_URL="$PROMETHEUS_RW_URL" -e K6_PROMETHEUS_RW_TREND_STATS="$PROMETHEUS_RW_TREND_STATS" -i grafana/k6 run -o experimental-prometheus-rw - < load/k6.js
fi

if command -v hey >/dev/null 2>&1; then
  exec hey -z 60s -c 8 http://localhost:5055/checkout
fi

echo 'Instale k6 ou hey para gerar carga.' >&2
exit 1
