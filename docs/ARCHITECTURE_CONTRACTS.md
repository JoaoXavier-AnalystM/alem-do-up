# Contratos arquiteturais

Contratos consumidos por Dock, Pulse, Forge, Chaos e Sentinel. Mudança
incompatível exige atualização deste documento e issue de arquitetura.

## 1. Contrato HTTP de saúde

### `/livez`

Sinal de processo.

- `GET /livez`.
- `200` quando processo aceita requests.
- Não consulta PostgreSQL.
- Não representa saúde da jornada.
- Docker liveness deve usar este endpoint.

### `/readyz`

Sinal de dependências obrigatórias.

- `GET /readyz`.
- `200` quando pool está criado e teste mínimo de banco passa.
- `503` quando banco, pool ou inicialização ainda não estão prontos.
- Saturação de pool durante incidente não torna API não pronta; readiness mede
  dependência e inicialização, não sucesso de negócio.
- Resposta JSON estável:

```json
{
  "status": "ready",
  "database": "ready",
  "pool": {
    "size": 5,
    "in_use": 0,
    "waiting": 0
  }
}
```

Campos adicionais são permitidos. Renomear campos existentes exige revisão
Atlas.

### `/health`

Sinal técnico legível por operador, sem substituir liveness/readiness.

- `200` enquanto API consegue responder, inclusive durante degradação de
  negócio.
- Corpo informa estado de negócio e causa.
- Pool cheio não transforma liveness em `503`.
- `503` fica reservado para API incapaz de responder ou modo offline explícito
  do cenário demo, conforme decisão Forge/Pulse.

```json
{
  "status": "degraded",
  "business_status": "degraded",
  "cause": "db_pool_exhausted",
  "pool_exhausted": true,
  "pool_in_use": 5,
  "pool_waiting": 3,
  "pool_size": 5,
  "mode": "incident"
}
```

### `/checkout`

Jornada de negócio.

- `200`: operação concluída.
- `503`: falha transitória de pool/banco ou offline demo.
- Erro deve possuir código estável, por exemplo:

```json
{
  "detail": {
    "code": "db_pool_exhausted",
    "retryable": true,
    "message": "checkout temporarily unavailable"
  }
}
```

Aquisição de conexão precisa ter timeout finito. Nenhum request pode esperar
indefinidamente por pool.

### `/metrics`

- `200` em formato Prometheus.
- Não depende de Grafana, Loki, Jaeger ou Collector.
- Scrape direto em `api:8000` mede serviço; probe por Nginx mede entrada.

## 2. Contrato do controlador demo

Controlador é fronteira lógica neste commit. Separação em serviço/container é
responsabilidade de Dock/Forge conforme issue #4.

Modos válidos:

```text
normal -> degraded -> incident -> offline
                  \-> progressive (orquestra transições)
```

Regras:

- Controlador só existe quando `DEMO_MODE=true`.
- `/demo/state` e `/demo/hold` são administrativos.
- Rotas não devem ser acessíveis sem autenticação ou rede administrativa.
- `POST /checkout` não deve alterar modo por contagem de submissões fora do
  cenário demo.
- `normal` deve cancelar progressão e permitir recuperação.
- Saturação de pool e banco indisponível são cenários distintos.

## 3. Contrato de métricas

Nomes estáveis:

```text
checkout_http_requests_total{path,method,status}
checkout_http_request_duration_seconds{path}
checkout_errors_total{reason}
checkout_db_pool_in_use
checkout_db_pool_waiting
checkout_db_pool_size
checkout_demo_incident
```

Regras:

- Labels têm cardinalidade limitada; nunca incluir request ID, usuário ou URL
  arbitrária.
- `in_use` e `waiting` devem convergir após sucesso, timeout, exceção e
  recovery.
- Erros devem distinguir `db_pool_exhausted`, `database_unavailable`,
  `service_offline` e erro interno.
- Métricas sintéticas devem possuir nome ou label que indique cenário demo.

SLIs mínimos:

- disponibilidade de `/checkout`;
- p95 de `/checkout`;
- taxa de erro por razão;
- razão `pool_waiting / pool_size`;
- probe da entrada Nginx;
- readiness da API.

## 4. Contrato de logs

Logs em JSON no stdout da API. Eventos conhecidos:

```text
database_pool_ready
database_waiting
db_pool_exhausted
checkout_failed
checkout_unavailable
demo_state_changed
demo_progression_stage
```

Campos recomendados:

```json
{
  "event": "db_pool_exhausted",
  "service": "checkout-api",
  "mode": "incident",
  "pool_in_use": 5,
  "pool_waiting": 3,
  "pool_size": 5,
  "request_id": "optional"
}
```

Promtail/Loki são consumidores. Falha de Loki não deve bloquear stdout nem
resposta HTTP.

## 5. Contrato de traces

- `service.name=checkout-api`.
- FastAPI cria span de rota.
- asyncpg cria span de operação SQL.
- Erros HTTP e timeout de pool marcam span como erro e carregam razão.
- OTLP é best effort; Collector indisponível não derruba checkout.

## 6. Contrato de dependências

| Dependência | Tipo | Falha permitida sem derrubar checkout |
| --- | --- | --- |
| PostgreSQL | síncrona, obrigatória | Não; API fica não pronta ou retorna 503 controlado |
| Nginx | síncrona, entrada | Não para usuários via entrypoint |
| Prometheus | assíncrona | Sim |
| Loki/Promtail | assíncrona | Sim |
| Collector/Jaeger | assíncrona | Sim |
| Grafana | consulta | Sim |
| Zabbix | opcional | Sim |
| Cloudflare | publicação externa | Apenas acesso público; acesso local continua possível |
| OpenDockWatch | operação host | Sim |

## 7. Critérios de gate

### Dock

- Implementa `/livez` e `/readyz` no healthcheck/orquestração.
- Codifica dependências críticas no Compose.
- Não faz API depender de observabilidade.

### Pulse

- Mede serviço e jornada separadamente.
- Adiciona probes, alertas e dashboards sem tornar Grafana requisito de runtime.

### Forge

- Implementa erros estruturados e timeout de pool.
- Mantém contratos HTTP e métricas estáveis.

### Chaos

- Usa somente controlador autorizado.
- Prova estados `normal`, `degraded`, `incident`, `recovered`.

### Sentinel

- Valida stack com observabilidade disponível e indisponível.
- Valida acesso local sem Cloudflare e publicação externa com Cloudflare.
