#!/usr/bin/env bash
set -euo pipefail

export DOCKER_BUILDKIT=1
COMPOSE="docker compose --profile zabbix"

for command in docker; do
  if ! command -v "$command" >/dev/null 2>&1; then
    echo "Comando obrigatório ausente: $command" >&2
    exit 1
  fi
done

if [ ! -f .env ]; then
  echo "Arquivo .env ausente; crie-o a partir de .env.example e preencha credenciais." >&2
  exit 1
fi

$COMPOSE config --quiet

for variable in APP_DB_NAME APP_DB_USER APP_DB_PASSWORD ZBX_DB_NAME ZBX_DB_USER ZBX_DB_PASSWORD GRAFANA_ADMIN_PASSWORD; do
  if ! grep -Eq "^${variable}=.+$" .env; then
    echo "Variável obrigatória ausente ou vazia no .env: ${variable}" >&2
    exit 1
  fi
done

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

if [ "${api_health:-}" != "healthy" ]; then
  echo "A API não ficou saudável." >&2
  exit 1
fi

# Fase 2: sobe monitoramento, observabilidade e Zabbix.
$COMPOSE up -d --remove-orphans --no-build zabbix-db jaeger loki prometheus promtail
$COMPOSE up -d --force-recreate --no-build otel-collector

# Por último inicia o proxy e as interfaces.
$COMPOSE up -d --remove-orphans --no-build nginx grafana zabbix-server zabbix-web zabbix-agent2
$COMPOSE ps

for attempt in $(seq 1 30); do
  nginx_health="$(docker inspect --format '{{.State.Health.Status}}' nginx 2>/dev/null || true)"
  if [ "$nginx_health" = "healthy" ]; then
    break
  fi
  if [ "$attempt" -eq 30 ]; then
    echo "O Nginx não ficou saudável a tempo." >&2
    docker logs --tail 100 nginx || true
    exit 1
  fi
  sleep 2
done

if [ "${nginx_health:-}" != "healthy" ]; then
  echo "O Nginx não ficou saudável." >&2
  exit 1
fi

echo "API: http://localhost:5055 | Grafana: http://localhost:${GRAFANA_PORT:-3000} | Jaeger: http://localhost:16686"
