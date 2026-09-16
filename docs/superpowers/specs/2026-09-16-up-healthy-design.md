# Seu sistema está UP. Mas ele está saudável? — Design

## Objetivo

Criar um laboratório reproduzível para uma palestra de observabilidade. O cenário mostra uma cadeia User → Nginx → Checkout API → PostgreSQL em que disponibilidade e recursos básicos continuam verdes enquanto o pool de conexões se esgota, elevando a latência e causando erros de checkout.

## Arquitetura

```text
                 métricas       traces       logs
User ──> Nginx ─────────────> Checkout API ─────────────> PostgreSQL
  │         │                      │                         │
  │         └── Zabbix             ├── Prometheus             │
  │                                ├── OTEL Collector         │
  └── hey/k6                        └── Loki/Promtail          │
```

O caminho principal é Docker Compose. A API FastAPI usa um pool explícito de conexões PostgreSQL, expõe `/health`, `/metrics` e endpoints de checkout/demo, escreve logs JSON e cria spans OpenTelemetry. O incidente é controlado por configuração e por endpoints locais de demonstração, sem depender de uma falha aleatória.

## Estados da demonstração

1. **Normal:** pool disponível, checkout rápido, health 200.
2. **Incidente:** requisições de demonstração ocupam conexões por tempo configurável. A saúde básica ainda retorna 200, mas `pool_waiting`, p95 e error rate sobem.
3. **Recuperação:** novas ocupações são interrompidas, conexões terminam e as séries retornam gradualmente ao normal.

## Componentes

- `demo/api`: FastAPI, asyncpg, prometheus-client, structlog e OpenTelemetry.
- `demo/nginx`: reverse proxy público para a API.
- `observability/prometheus`: scrape da API e regras/alerta didático.
- `observability/grafana`: datasource e dashboard provisionados sem cliques manuais.
- `observability/loki` + Promtail: logs JSON pesquisáveis.
- `observability/otel-collector`: recebe OTLP e exporta traces para Jaeger.
- `observability/zabbix`: disponibilidade e infraestrutura básica, com template/import documentado.
- `scripts`: subir, mudar estado, gerar carga, verificar e capturar evidências.

## Requisitos de apresentação

O README e `presentation/` precisam conter diagramas ASCII, URLs, comandos copiáveis, checkpoints visuais e fallback de screenshots/gravação. O material deve explicar métricas, logs e traces para iniciantes sem esconder conceitos úteis para profissionais.

## Verificação

- Testes unitários da máquina de estados e do contrato do health endpoint.
- `docker compose config` para validar a topologia.
- Script de smoke test para health, métricas e fluxo de checkout.
- Sequência documentada para demonstrar normal → incidente → recuperação.

