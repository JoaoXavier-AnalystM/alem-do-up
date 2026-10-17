# Seu sistema está UP. Mas ele está saudável?

Laboratório de observabilidade para uma palestra. A demonstração separa
disponibilidade técnica da saúde da jornada de checkout.

```text
Usuário → Nginx → Checkout API → PostgreSQL
                    ↓
       métricas · logs · traces · alertas
```

## Contrato local

- `/health` retorna HTTP 200 em `normal`, `degraded` e `incident`, inclusive
  quando o pool está sob pressão. O JSON pode informar `status: degraded` e
  `pool_saturated: true` sem derrubar a liveness.
- `/checkout` retorna 200 normalmente, fica lento em `degraded` e pode retornar
  503 quando o pool esgota ou o modo chega ao limiar crítico.
- `incident` ocupa conexões do pool; `load` aumenta a pressão; `recover` volta
  para `normal`, cancela holders e zera contadores de pressão.
- `offline` é o único modo de demonstração que retorna 503 em `/health`.
- `/metrics` expõe RED HTTP e `checkout_db_pool_*` para Prometheus.

Valores padrão do laboratório: `DB_POOL_MAX=5`,
`INCIDENT_HOLD_SECONDS=8`, degradação após 5 cadastros, incidente após 12 e
offline após 22. Variáveis estão em `.env.example`.

## Subir o laboratório

Requisitos: Docker Engine com Docker Compose, Bash e `curl`. Para carga, use
`k6` ou `hey`.

```bash
cp .env.example .env
docker compose config --quiet
chmod +x scripts/*.sh
./scripts/up.sh
./scripts/smoke.sh
```

`scripts/up.sh` usa o `docker-compose.yml` principal, sobe a API e o
monitoramento, e inclui o perfil Zabbix. `scripts/smoke.sh` verifica
`/health`, `/metrics` e `/checkout`.

## Roteiro normal → incidente → recuperação

```bash
./scripts/normal.sh
./scripts/incident.sh
K6_INCIDENT=true K6_VUS=50 K6_DURATION=5m ./scripts/load.sh
./scripts/recover.sh
```

`scripts/load.sh` prefere `k6`, usa k6 em container quando Docker está
disponível e cai para `hey` como alternativa. `K6_INCIDENT=true` ativa o modo
incidente no `setup` do teste k6. Para carga curta, use por exemplo:

```bash
K6_INCIDENT=true K6_VUS=8 K6_DURATION=30s ./scripts/load.sh
```

Durante a pressão, compare `/health` com `/checkout`: o processo continua
respondendo enquanto a jornada pode ficar lenta ou falhar.

Para validar o contrato do repositório em uma única entrada, execute
`scripts/validate-repository.sh`. Com Docker ausente, ele roda os testes
estáticos e informa que a validação de Compose foi ignorada.

## Portas e acessos

| Serviço | Acesso local | Papel |
| --- | --- | --- |
| Nginx / API | `http://localhost:5055` (`APP_PORT`) | `/health`, `/metrics`, `/checkout`, `/comprar`, `/demo` |
| API interna | `api:8000` | upstream do Nginx |
| PostgreSQL | `db:5432` | pool da API; não publicado no host |
| Grafana | `http://localhost:3000` (`GRAFANA_PORT`) | dashboards |
| Prometheus | `http://localhost:9090` | métricas e alertas |
| Loki | `http://localhost:3100` | logs |
| Jaeger | `http://localhost:16686` | traces |
| OTLP | `localhost:4317` / `localhost:4318` | ingestão de traces |
| Zabbix web | `http://localhost:8081` (`ZBX_WEB_PORT`) | perfil opcional usado pelo `up.sh` |
| Zabbix server | `localhost:10051` (`ZBX_SERVER_PORT`) | perfil opcional |
| Zabbix agent | `127.0.0.1:10150` (`ZBX_AGENT_PORT`) | perfil opcional |
| OpenDockWatch | `http://localhost:3001` | stack separado |

O caminho da interface é controlado por `APP_UI_PREFIX` no `.env` e é
repassado pelo Compose à API. O padrão local é `/demo`; `/` continua sendo a
visão macro e `/comprar` a jornada do usuário.

OpenDockWatch possui Compose e ciclo de vida próprios em `opendockwatch/`; não
é iniciado pelo stack principal. Ele precisa do socket Docker do host e deve
ficar protegido.

## Evidências

No Grafana, use os dashboards da pasta `DIA D` para correlacionar p95,
erros, pool em uso, pool aguardando e saúde técnica. No Loki, procure
`pool_exhausted`; no Jaeger, selecione o serviço `checkout-api` e abra um
trace de `/checkout`.

O dashboard e o app usam UIDs provisionados para `prometheus`, `loki`,
`jaeger`, `postgres` e Zabbix. As queries principais usam
`checkout_http_*`, `checkout_errors_total` e `checkout_db_pool_*`.

## Limitações do ambiente

- O fluxo completo depende de Docker, volumes, rede Compose e PostgreSQL.
- Sem Docker, é possível validar arquivos, testes e documentação, mas não
  executar `docker compose config`, containers ou o fluxo end-to-end.
- `promtail` precisa do socket Docker e dos logs de containers.
- `scripts/load.sh` não gera carga sem `k6`, Docker funcional ou `hey`.
- Os valores de `.env.example` são credenciais somente para demonstração.
  Troque-os antes de qualquer uso real.

Arquitetura detalhada: `docs/ARCHITECTURE.md`.

## Limpeza

```bash
docker compose down -v
```
