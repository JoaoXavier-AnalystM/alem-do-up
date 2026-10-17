# Além do UP — laboratório observável

## Intent

Demonstrar, de forma reproduzível, que disponibilidade técnica não prova saúde
da jornada de checkout. Durante o incidente, `/health` continua respondendo,
enquanto `/checkout` espera ou falha por saturação controlada do pool PostgreSQL.

## Scope

- Preservar FastAPI, PostgreSQL/TimescaleDB, Nginx, Docker Compose, Prometheus,
  Grafana, Loki, Jaeger e OpenTelemetry.
- Manter Zabbix e OpenDockWatch opcionais e isolados do caminho principal.
- Usar controles simples: normal, incident, load e recover.
- Correlacionar métricas, logs e traces usando request ID e trace ID.

## Demo contract

1. `scripts/up.sh` sobe stack principal.
2. `scripts/smoke.sh` prova `/health`, `/metrics` e checkout normal.
3. `scripts/incident.sh` ativa incidente e aguarda pool ocupado.
4. `/health` permanece HTTP 200 durante pressão de pool.
5. `/checkout` apresenta latência maior e/ou HTTP 503 sob carga.
6. Prometheus mostra RED e pool; Loki mostra `pool_exhausted`; Jaeger mostra
   espera/operação de banco.
7. `scripts/recover.sh` cancela holders, aguarda pool livre e prova retorno.

## Non-goals

- Criar sistema de checkout de produção.
- Adicionar broker, service mesh ou banco extra.
- Expor controles de caos sem proteção em ambiente público.
- Prometer validação Docker neste host quando Docker não estiver instalado.

## Invariants

- Holders sempre liberam contadores em `finally`.
- Recovery é idempotente.
- Carga não deixa modo persistente após recuperação.
- Falhas HTTP aparecem com status correto nas métricas.
- Segredos reais nunca entram no repositório.
- Alteração local pré-existente em `observability/grafana/dashboards/DIA D/02-banco-api-ok.json` permanece intocada.

## Acceptance evidence

- Testes unitários cobrindo estado normal, incidente, recovery e cleanup.
- JSON/YAML e Python compilam.
- `docker compose config` e fluxo completo executam em host com Docker.
- Dashboard, logs e traces apontam para mesma janela de incidente.
