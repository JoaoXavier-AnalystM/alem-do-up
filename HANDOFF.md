# Handoff — laboratório “Seu sistema está UP. Mas ele está saudável?”

## Goal

Continuar o desenvolvimento do laboratório de palestra em `D:\codex\up-but-not-healthy`, mantendo o contexto da conversa original. O projeto demonstra User → Nginx → Checkout API → PostgreSQL tecnicamente UP, mas degradado por esgotamento do pool de conexões.

## Current Progress

- Repositório criado e movido para `D:\codex\up-but-not-healthy`.
- Docker Compose principal criado com API, PostgreSQL/TimescaleDB, Nginx, Prometheus, Grafana, Loki/Promtail, Jaeger, OTEL Collector e Zabbix 7.4.
- Senhas não ficam no Compose: são exigidas via `.env`.
- Grafana configurado para `12.1.3-security-01`.
- Plugin Zabbix configurado como `alexanderzobnin-zabbix-app:6.0.3`.
- Datasources provisionados: Prometheus, Loki, Jaeger, PostgreSQL/TimescaleDB e Zabbix.
- Banco da aplicação usa `timescale/timescaledb:latest-pg17` e inicializa TimescaleDB via `demo/db/initdb/001-timescale.sql`.
- Banco do Zabbix usa `postgres:17.7-alpine`.
- API FastAPI em `demo/api/app.py`, com health, métricas Prometheus, logs estruturados, pool controlado e tracing OTEL.
- Scripts shell de demonstração em `scripts/` e carga em `load/k6.js`.
- Roteiro em `presentation/` e arquitetura em `ARCHITECTURE.md`.

## What Worked

- Compose com `service_healthy` para PostgreSQL e `service_started` para Zabbix Server durante importação inicial do schema.
- `GF_INSTALL_PLUGINS: alexanderzobnin-zabbix-app:6.0.3`.
- Datasource secrets via `$__env{VAR}` no provisionamento Grafana.
- Healthchecks com `start_period`, logs rotacionados e `no-new-privileges`.
- Agent 2 mantido sem `privileged`, `pid: host` e sem Docker socket.

## What Didn’t Work

- O workspace desta conversa permanece vinculado ao espelho antigo em `C:\Users\joaox\.codex\.chatgpt-projects\...`; mover os arquivos não troca o workspace da conversa.
- Docker não está instalado no ambiente atual; ainda falta executar `docker compose config` e subir a stack numa VM/host com Docker.
- Pytest não estava instalado quando os testes foram tentados.
- O commit Git não foi criado porque o sandbox bloqueou escrita no índice `.git`; o repositório e os arquivos existem no novo diretório.

## Continuation Update (2026-09-16)

- Corrigido o contrato de `POST /demo/state`: agora recebe o JSON documentado (`{"mode":"normal"}` ou `{"mode":"incident"}`), compatível com os scripts shell.
- Adicionado teste unitário para o payload JSON do endpoint.
- Serviços `zabbix-db`, `zabbix-server`, `zabbix-web` e `zabbix-agent2` agora usam o perfil Compose `zabbix`, alinhado ao comando documentado.
- Fluxos operacionais convertidos para `.sh` com `curl`, `k6` e fallback `hey`, voltados à VPS Ubuntu.
- Validações locais concluídas: YAML do Compose parseia e Python compila.
- Validações pendentes no host Docker: `docker compose config`, subida da stack, smoke/fluxo completo e pytest.

## Next Steps

1. Abrir um novo workspace na IDE em `D:\codex\up-but-not-healthy`.
2. Abrir este arquivo primeiro: `D:\codex\up-but-not-healthy\HANDOFF.md`.
3. Criar `.env` a partir de `.env.example` e preencher `APP_DB_PASSWORD`, `ZBX_DB_PASSWORD`, `GRAFANA_ADMIN_PASSWORD`, `ZABBIX_API_USER` e `ZABBIX_API_PASSWORD`.
4. Executar `docker compose config`.
5. Executar `docker compose up -d --build`.
6. Validar `./scripts/smoke.sh` e a sequência `./scripts/normal.sh`, `./scripts/incident.sh`, `./scripts/load.sh`, `./scripts/recover.sh`.
7. Corrigir qualquer incompatibilidade real de imagem/plugin encontrada no host Docker.
8. Instalar pytest e executar os testes de `demo/api/tests/`.
9. Fazer o primeiro commit local e, se desejado, publicar no GitHub.

## Important Constraints

- Nunca colocar senhas reais em Compose, README, dashboards ou Git.
- `sources/` do projeto ChatGPT original é somente referência e deve permanecer intocado.
- Não habilitar privilégios amplos no Zabbix Agent sem uma decisão explícita de segurança.
