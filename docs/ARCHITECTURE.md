# Arquitetura

```text
cliente / k6 / hey
        │ localhost:${APP_PORT:-5055}
        ▼
   Nginx :80 ───────► Checkout API :8000 ───────► PostgreSQL :5432
        │                     │                         │
        │                     ├── metrics ───────────► Prometheus :9090
        │                     ├── logs ──────────────► Loki :3100
        │                     └── traces ────────────► OTLP → Jaeger :4317
        │
        ├── Grafana :3000
        ├── Jaeger UI :16686
        └── Zabbix :8081 / :10051 / :10150 (perfil opcional)
```

O stack principal é definido em `docker-compose.yml`. A API e o banco ficam
na rede interna `lab`; o host publica Nginx, Grafana, Prometheus, Loki, Jaeger
e as portas do perfil Zabbix. OpenDockWatch fica fora desse grafo, em
`opendockwatch/`, com acesso separado em `localhost:3001`.

## Caminho da requisição

1. Cliente chama `http://localhost:5055`.
2. Nginx encaminha para `api:8000`.
3. A API processa `/checkout`, adquire conexão do pool e executa a operação
   PostgreSQL.
4. Middleware registra status, duração e request ID.
5. Prometheus coleta `/metrics`; Promtail envia logs ao Loki; OpenTelemetry
   envia spans ao Jaeger.

Rotas usadas no laboratório:

| Rota | Contrato |
| --- | --- |
| `/health` | liveness/processo e estado demonstrativo do pool |
| `/metrics` | métricas Prometheus, incluindo `checkout_db_pool_*` |
| `/checkout` | jornada de checkout GET usada por smoke e carga |
| `/checkout` POST | cadastro da jornada em `/comprar` |
| `/demo/state` | `normal`, `degraded`, `incident`, `offline` ou `progressive` |
| `/demo/hold` | ocupa uma conexão durante `incident` |
| `/demo` | visão macro; prefixo definido por `APP_UI_PREFIX` |
| `/comprar` | formulário da jornada do usuário |

## Pressão do pool

O padrão é `DB_POOL_MAX=5`. `scripts/incident.sh` chama
`POST /demo/state {"mode":"incident"}` e envia cinco holds assíncronos,
coerentes com o pool padrão. O script de carga pode ativar o incidente pelo
`setup` do k6 com `K6_INCIDENT=true`.

Durante `incident`:

- `/health` permanece HTTP 200 enquanto o processo responde, mesmo com pool
  saturado;
- o payload pode mudar para `status: degraded`, com `journey_status` e
  `pool_saturated` indicando o sintoma;
- `/checkout` pode aguardar o timeout de aquisição e retornar HTTP 503 com
  `checkout database pool exhausted`;
- `/metrics` mostra `checkout_db_pool_in_use`,
  `checkout_db_pool_waiting`, `checkout_db_pool_size`, latência e erros;
- logs JSON incluem `pool_exhausted` e `checkout_failed`;
- traces mostram a espera/operação de banco no serviço `checkout-api`.

`offline` retorna HTTP 503 em `/health` e `/checkout`. `degraded` mantém
HTTP 200, mas adiciona atraso de negócio. Os limiares de cadastro são
`DEMO_DEGRADED_AFTER`, `DEMO_CRITICAL_AFTER` e `DEMO_OFFLINE_AFTER`.

## Recuperação

`scripts/recover.sh` envia `normal` para `/demo/state`. A API cancela a
progressão e os holders, limpa `pool_in_use` e `waiting`, e pode receber a
mesma operação novamente sem mudar o resultado. Valide `/health` 200,
`/checkout` 200 e a queda dos sinais no Grafana.

Scripts do fluxo: `scripts/incident.sh`, `scripts/load.sh` e
`scripts/recover.sh`. O fluxo completo e os pré-requisitos estão no
`README.md`.

## Portas

| Componente | Porta local | Observação |
| --- | --- | --- |
| Nginx | `5055` por padrão | `APP_PORT`; entrada pública do laboratório |
| API | `8000` | somente rede Compose |
| PostgreSQL | `5432` | somente rede Compose |
| Grafana | `3000` por padrão | `GRAFANA_PORT` |
| Prometheus | `9090` | scrape e alertas |
| Loki | `3100` | API de logs |
| Jaeger UI | `16686` | busca de traces |
| OTLP | `4317`, `4318` | gRPC e HTTP |
| Zabbix web/server/agent | `8081`, `10051`, `10150` | perfil `zabbix` |
| OpenDockWatch | `3001` | Compose separado |

## Limitações e fronteiras

Docker Compose, volumes, rede e PostgreSQL são pré-requisitos do runtime.
Sem Docker, QA pode fazer parse de JSON/YAML, checar referências e rodar
testes estáticos, mas não pode provar `docker compose config`, healthchecks,
rede, logs, traces ou o fluxo end-to-end. Não trate essa validação parcial
como teste de disponibilidade.

`APP_UI_PREFIX` está em `.env.example` e é repassado pelo Compose. O padrão é
`demo`, portanto a visão macro local é `/demo`. O domínio público/Cloudflare
não faz parte do contrato local.
