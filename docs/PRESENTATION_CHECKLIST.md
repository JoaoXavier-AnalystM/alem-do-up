# Checklist da apresentação

Roteiro local, reproduzível e baseado no contrato do repositório. Use os
domínios públicos apenas quando o ambiente publicado estiver disponível; os
acessos abaixo são a referência local.

## 1. Preparação

- [ ] Copiar `.env.example` para `.env`.
- [ ] Validar Compose com `docker compose config --quiet`.
- [ ] Subir com `scripts/up.sh`.
- [ ] Executar `scripts/smoke.sh`.
- [ ] Rodar `scripts/validate-repository.sh` para QA estático e Compose.
- [ ] Confirmar que Docker, Bash e `curl` estão disponíveis.
- [ ] Para carga, confirmar `k6` ou `hey`.

```bash
cp .env.example .env
docker compose config --quiet
chmod +x scripts/*.sh
./scripts/up.sh
./scripts/smoke.sh
./scripts/validate-repository.sh
```

Se Docker não estiver instalado, marque a preparação como parcial. Testes
estáticos não substituem healthchecks, rede ou o fluxo end-to-end.

## 2. Acessos locais

- [ ] Visão macro: <http://localhost:5055/>.
- [ ] Saúde: <http://localhost:5055/health>.
- [ ] Índice técnico: <http://localhost:5055/checkout-api>.
- [ ] Jornada do usuário: <http://localhost:5055/comprar>.
- [ ] Grafana: <http://localhost:3000>.
- [ ] Prometheus: <http://localhost:9090>.
- [ ] Loki: <http://localhost:3100>.
- [ ] Jaeger: <http://localhost:16686>.
- [ ] OpenDockWatch separado: <http://localhost:3001>.
- [ ] Zabbix web, quando o perfil estiver ativo: <http://localhost:8081>.

O prefixo configurável por `APP_UI_PREFIX` tem padrão `/demo`. A raiz `/`
continua sendo a visão macro usada pela apresentação.

## 3. Estado normal

- [ ] Executar `scripts/normal.sh`.
- [ ] Confirmar `/health` HTTP 200 com `status: ok`.
- [ ] Confirmar `/checkout` HTTP 200 e baixa latência.
- [ ] Confirmar pool livre e ausência de erros recentes.
- [ ] Capturar visão macro e resposta do `/health`.

## 4. Incidente controlado

- [ ] Executar `scripts/incident.sh`.
- [ ] Confirmar pool em uso e requisições aguardando.
- [ ] Confirmar que `/health` continua HTTP 200 sob pressão.
- [ ] Confirmar que o JSON pode indicar `status: degraded` e
      `pool_saturated: true`.
- [ ] Confirmar que `/checkout` fica lento ou retorna 503 por pool esgotado.

Para carga k6 local:

```bash
K6_INCIDENT=true K6_VUS=50 K6_DURATION=5m K6_TEST_ID=checkout-heavy ./scripts/load.sh
```

Para uma rodada curta:

```bash
K6_INCIDENT=true K6_VUS=8 K6_DURATION=30s ./scripts/load.sh
```

`scripts/load.sh` usa `load/k6.js`, ou k6 em container, ou `hey`. Sem uma
dessas opções, a carga não será gerada.

Para progressão gradual, use `scripts/gradual.sh`. A sequência mantém o
checkout respondendo enquanto adiciona VUs:

```bash
GRADUAL_MAX_VUS=8 GRADUAL_STEP_DURATION=20s ./scripts/gradual.sh
```

## 5. Dashboards e sinais

Abra, nesta ordem:

1. `observability/grafana/dashboards/DIA D/01-servidor-ok.json` — servidor.
2. `observability/grafana/dashboards/DIA D/02-banco-api-ok.json` — banco, API
   e pool.
3. `observability/grafana/dashboards/DIA D/03-visao-operacional.json` — visão
   operacional.
4. `observability/grafana/dashboards/DIA D/04-traces-logs-metricas-erros.json`
   — traces, logs, métricas e erros.
5. `observability/grafana/dashboards/k6-load.json` — carga k6.

Confirme durante a pressão:

- p95 de `/checkout`;
- `checkout_db_pool_in_use`, `checkout_db_pool_waiting` e tamanho do pool;
- sucessos e 503 em `checkout_http_requests_total`;
- `checkout_errors_total`;
- scrape técnico `up{job="checkout-api"}`;
- VUs, req/s, checks e p95 do k6.

UIDs provisionados esperados: `prometheus`, `loki`, `jaeger`, `postgres` e
`dfyxo4mmoy8lce` para Zabbix.

## 6. Logs e traces

- [ ] No Loki, executar `{container="api-up"} |= "pool"`.
- [ ] Procurar o evento `pool_exhausted`.
- [ ] Procurar `checkout_failed` e correlacionar horário com o p95.
- [ ] No Jaeger, selecionar `checkout-api`.
- [ ] Abrir um trace de `/checkout` e localizar a operação de banco.

Os dashboards 03 e 04 filtram o evento emitido `pool_exhausted`. Se uma cópia
antiga mostrar `db_pool_exhausted`, substitua pelo nome atual
`pool_exhausted` antes da apresentação.

## 7. Recuperação

- [ ] Executar `scripts/recover.sh`.
- [ ] Confirmar `/health` HTTP 200 e `/checkout` HTTP 200.
- [ ] Confirmar pool `in_use=0` e `waiting=0` após drenagem.
- [ ] Confirmar que não surgem novos erros de pool.
- [ ] Repetir `scripts/recover.sh` para verificar idempotência.
- [ ] Capturar painel final e resposta do `/health`.

Mensagem final: infraestrutura online não prova que a jornada do usuário está
saudável. O pool, a latência, os erros, logs e traces mostram a experiência.
