#!/usr/bin/env bash
set -euo pipefail

export DOCKER_BUILDKIT=1
COMPOSE="docker compose --profile zabbix"

# Migração dos nomes antigos; volumes e dados permanecem intactos.
for old_container in checkout-db checkout-api checkout-nginx checkout-prometheus checkout-grafana checkout-loki checkout-promtail checkout-jaeger checkout-otel-collector checkout-zabbix-db checkout-zabbix-server checkout-zabbix-web checkout-zabbix-agent2; do
  docker rm -f "$old_container" 2>/dev/null || true
done

$COMPOSE up -d --remove-orphans --no-build db zabbix-db jaeger loki prometheus promtail otel-collector
$COMPOSE up -d --build api
$COMPOSE up -d --remove-orphans --no-build nginx grafana zabbix-server zabbix-web zabbix-agent2
$COMPOSE ps

echo "API: http://localhost:5055 | Grafana: http://localhost:3000 | Jaeger: http://localhost:16686"
