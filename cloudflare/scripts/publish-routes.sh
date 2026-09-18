#!/usr/bin/env bash
set -euo pipefail

: "${CLOUDFLARE_API_TOKEN:?CLOUDFLARE_API_TOKEN is required}"
: "${CLOUDFLARE_ACCOUNT_ID:?CLOUDFLARE_ACCOUNT_ID is required}"
: "${CLOUDFLARE_TUNNEL_ID:?CLOUDFLARE_TUNNEL_ID is required}"
: "${CLOUDFLARE_ZONE_ID:?CLOUDFLARE_ZONE_ID is required}"
: "${CLOUDFLARE_DOMAIN:?CLOUDFLARE_DOMAIN is required}"
: "${CLOUDFLARE_ORIGIN_HOST:?CLOUDFLARE_ORIGIN_HOST is required}"

API="https://api.cloudflare.com/client/v4"
CLOUDFLARE_API_TOKEN="$(printf '%s' "$CLOUDFLARE_API_TOKEN" | tr -d '\r\n')"
APP_HOST="aplicacao-ps.${CLOUDFLARE_DOMAIN}"
GRAFANA_HOST="grafana-ps.${CLOUDFLARE_DOMAIN}"
TUNNEL_TARGET="${CLOUDFLARE_TUNNEL_ID}.cfargotunnel.com"

cf() {
  curl --fail-with-body -sS \
    -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
    -H "Content-Type: application/json" \
    "$@"
}

token_check="$(cf "${API}/user/tokens/verify" || true)"
if ! printf '%s' "$token_check" | jq -e '.success == true' >/dev/null; then
  echo "CLOUDFLARE_API_TOKEN rejeitado. Use o token da API do Cloudflare, nao o token do Tunnel." >&2
  exit 1
fi

echo "Atualizando rotas do Tunnel para ${APP_HOST} e ${GRAFANA_HOST}"

current_config="$(cf "${API}/accounts/${CLOUDFLARE_ACCOUNT_ID}/cfd_tunnel/${CLOUDFLARE_TUNNEL_ID}/configurations")"
config_payload="$(printf '%s' "$current_config" | jq \
  --arg app_host "$APP_HOST" \
  --arg grafana_host "$GRAFANA_HOST" \
  --arg origin_host "$CLOUDFLARE_ORIGIN_HOST" \
  '.result.config.ingress // []
   | map(select(.hostname != $app_host and .hostname != $grafana_host and .service != "http_status:404"))
   | . + [
       {"hostname": $app_host, "service": ("http://" + $origin_host + ":5055")},
       {"hostname": $grafana_host, "service": ("http://" + $origin_host + ":3030")},
       {"service": "http_status:404"}
     ]
   | {"config": {"ingress": .}}')"

cf -X PUT \
  "${API}/accounts/${CLOUDFLARE_ACCOUNT_ID}/cfd_tunnel/${CLOUDFLARE_TUNNEL_ID}/configurations" \
  --data "$config_payload" >/dev/null

upsert_cname() {
  local hostname="$1"
  local existing
  local record_id
  local body

  existing="$(cf --get "${API}/zones/${CLOUDFLARE_ZONE_ID}/dns_records" \
    --data-urlencode "type=CNAME" \
    --data-urlencode "name=${hostname}")"
  record_id="$(printf '%s' "$existing" | jq -r '.result[0].id // empty')"
  body="$(jq -n \
    --arg name "$hostname" \
    --arg content "$TUNNEL_TARGET" \
    '{type: "CNAME", name: $name, content: $content, ttl: 1, proxied: true}')"

  if [ -n "$record_id" ]; then
    cf -X PUT "${API}/zones/${CLOUDFLARE_ZONE_ID}/dns_records/${record_id}" --data "$body" >/dev/null
  else
    cf -X POST "${API}/zones/${CLOUDFLARE_ZONE_ID}/dns_records" --data "$body" >/dev/null
  fi
  echo "DNS pronto: ${hostname} -> ${TUNNEL_TARGET}"
}

upsert_cname "$APP_HOST"
upsert_cname "$GRAFANA_HOST"
echo "Rotas Cloudflare publicadas com sucesso"
