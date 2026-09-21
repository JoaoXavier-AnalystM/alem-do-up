#!/usr/bin/env bash
set -euo pipefail

export DOCKER_BUILDKIT=1
COMPOSE="docker compose --profile zabbix"

# Migração dos nomes antigos; volumes e dados permanecem intactos.
for old_container in checkout-db checkout-api checkout-nginx checkout-prometheus checkout-grafana checkout-loki checkout-promtail checkout-jaeger checkout-otel-collector checkout-zabbix-db checkout-zabbix-server checkout-zabbix-web checkout-zabbix-agent2; do
  docker rm -f "$old_container" 2>/dev/null || true
done

# Fase 1: sobe somente o banco e a API.
$COMPOSE up -d --remove-orphans --no-build db
$COMPOSE up -d --build api

for attempt in $(seq 1 30); do
  api_health="$(docker inspect --format '{{.State.Health.Status}}' api-up 2>/dev/null || true)"
  if [ "$api_health" = "healthy" ]; then
    break
  fi
  if [ "$attempt" -eq 30 ]; then
    echo "A API não ficou saudável a tempo." >&2
    docker logs --tail 100 api-up || true
    exit 1
  fi
  sleep 2
done

# Fase 2: sobe monitoramento, observabilidade e Zabbix.
$COMPOSE up -d --remove-orphans --no-build zabbix-db jaeger loki prometheus promtail
$COMPOSE up -d --force-recreate --no-build otel-collector

# Por último inicia o proxy e as interfaces.
$COMPOSE up -d --remove-orphans --no-build nginx grafana zabbix-server zabbix-web zabbix-agent2
$COMPOSE ps

echo "API: http://localhost:5055 | Grafana: http://localhost:${GRAFANA_PORT:-3000} | Jaeger: http://localhost:16686"
