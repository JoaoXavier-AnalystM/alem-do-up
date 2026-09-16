# Seu sistema está UP. Mas ele está saudável? Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Entregar um laboratório Docker reproduzível e material visual para demonstrar esgotamento do pool de conexões.

**Architecture:** API FastAPI com PostgreSQL atrás de Nginx; Prometheus, Grafana, Loki/Promtail, OpenTelemetry/Jaeger e Zabbix são serviços Compose. Scripts controlam os estados e a carga.

**Tech Stack:** Docker Compose, Python 3.12, FastAPI, asyncpg, pytest, Prometheus, Grafana, Loki, Promtail, OpenTelemetry, Jaeger, Zabbix, hey/k6.

**Spec:** `docs/superpowers/specs/2026-09-16-up-healthy-design.md`

## Global Constraints

- O caminho principal deve ser Docker Compose.
- `sources/` é somente leitura.
- Health deve continuar retornando 200 durante parte do incidente.
- Métricas devem incluir HTTP p95, error rate e estado do pool.
- Logs devem permitir localizar timeout/pool exhausted.
- Tracing deve mostrar PostgreSQL consumindo a maior parte da latência.
- Todo fluxo deve estar explícito e visual em README/presentation.

### Task 1: Scaffolding e API demonstrável

**Files:** `demo/api/app.py`, `demo/api/requirements.txt`, `demo/api/Dockerfile`, `demo/api/tests/test_app.py`, `demo/api/__init__.py`

- [ ] Escrever testes da máquina de estados, health 200 durante degradação e métricas do pool.
- [ ] Rodar pytest e observar falha por arquivos ausentes.
- [ ] Implementar FastAPI, pool asyncpg, endpoints `/health`, `/checkout`, `/demo/state`, `/demo/hold`, `/metrics`.
- [ ] Rodar pytest e confirmar aprovação.
- [ ] Adicionar logs JSON e spans da operação PostgreSQL.

### Task 2: Compose e proxy

**Files:** `docker-compose.yml`, `demo/nginx/nginx.conf`, `.env.example`, `.dockerignore`

- [ ] Definir PostgreSQL, API, Nginx e observabilidade em Compose.
- [ ] Expor portas com tabela no README.
- [ ] Validar com `docker compose config`.

### Task 3: Observabilidade provisionada

**Files:** `observability/prometheus/*`, `observability/grafana/*`, `observability/loki/*`, `observability/promtail/*`, `observability/otel-collector/*`, `observability/jaeger/*`, `observability/zabbix/*`

- [ ] Provisionar datasources e dashboard Grafana.
- [ ] Configurar scrape Prometheus, Loki/Promtail e OTEL/Jaeger.
- [ ] Documentar Zabbix com itens de disponibilidade/infra.

### Task 4: Scripts de operação e verificação

**Files:** `scripts/*.sh`, `load/k6.js`

- [ ] Criar comandos normais, incidente, recuperação e carga.
- [ ] Criar smoke test que verifica os contratos públicos.
- [ ] Criar carga k6 e fallback hey.

### Task 5: Material visual da palestra

**Files:** `README.md`, `ARCHITECTURE.md`, `presentation/README.md`, `presentation/outline.md`, `presentation/screenshots/README.md`

- [ ] Escrever narrativa tudo verde → reclamação → p95 → pool → logs → trace → RCA → melhoria.
- [ ] Incluir roteiro de captura de screenshots/gravação e perguntas à plateia.
- [ ] Incluir checklist de publicação e troubleshooting.

### Task 6: Verificação final e versionamento

- [ ] Rodar testes, Compose config e smoke checks possíveis.
- [ ] Revisar árvore e garantir que `sources/` não foi alterado.
- [ ] Inicializar Git e registrar o primeiro commit local.
