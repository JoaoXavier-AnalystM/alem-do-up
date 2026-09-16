# Seu sistema está UP. Mas ele está saudável?

Laboratório reproduzível da palestra sobre a evolução de monitoramento para observabilidade. O incidente simula esgotamento do pool de conexões: User → Nginx → Checkout API → PostgreSQL continua tecnicamente de pé, mas o checkout fica lento e falha.

## Comece em Docker

Pré-requisitos: Docker Desktop com Compose. Opcionalmente, instale `k6` ou `hey` para carga.

```bash
cp .env.example .env
# Edite .env e preencha todas as variáveis *_PASSWORD antes de iniciar.
chmod +x scripts/*.sh
docker compose up -d --build
./scripts/smoke.sh
```

Abra:

| Tela | URL | O que observar |
|---|---|---|
| Aplicação | [localhost:8080](http://localhost:8080) | jornada e health |
| Grafana | [localhost:3000](http://localhost:3000) | p95, erros, pool, logs |
| Prometheus | [localhost:9090](http://localhost:9090) | consultas PromQL |
| Jaeger | [localhost:16686](http://localhost:16686) | PostgreSQL no trace |

## Roteiro visual em 3 comandos

```bash
./scripts/normal.sh
./scripts/incident.sh
./scripts/load.sh
./scripts/recover.sh
```

1. **Tudo verde:** `/health` 200, pool abaixo de 5, p95 baixo.
2. **Reclamação:** “o checkout demora 8 segundos”.
3. **Latência:** no Grafana, `HTTP p95` sobe antes de CPU/memória.
4. **Conexões:** `pool_in_use` encosta no tamanho e `pool_waiting` aparece.
5. **Logs:** Loki mostra `db_pool_exhausted` e `checkout_failed`.
6. **Trace:** Jaeger mostra o span PostgreSQL dominando a duração.
7. **RCA:** a aplicação segura conexões por mais tempo que a capacidade do pool.
8. **Melhoria:** monitorar jornada, p95, error rate, pool waiting e traces — não só ping/porta/CPU.

## Contratos da demo

- `/health`: saúde básica; começa em 200 durante o incidente e vira 503 quando o pool está completamente ocupado.
- `/checkout`: jornada de negócio; retorna 200 normal e pode retornar 503 sob exaustão.
- `/metrics`: métricas Prometheus, incluindo `checkout_http_request_duration_seconds`, `checkout_errors_total`, `checkout_db_pool_in_use`, `checkout_db_pool_waiting` e `checkout_db_pool_size`.
- `/demo/state`: `POST` com `{"mode":"normal"}` ou `{"mode":"incident"}`.
- `/demo/hold`: ocupa uma conexão de demonstração enquanto o modo incidente está ativo.

## Zabbix

Para a camada de disponibilidade/infra, o Compose inclui Zabbix Server, Web e Agent 2 sem privilégios de host:

```bash
docker compose --profile zabbix up -d
```

Consulte [observability/zabbix/README.md](observability/zabbix/README.md). O Zabbix mostra por que “UP” é uma evidência útil, mas insuficiente.

## Segredos

Nenhuma senha é definida no Compose. O arquivo `.env.example` contém somente nomes de variáveis vazias; preencha `.env` localmente e nunca o versione. Em ambiente de produção, prefira Docker Secrets/Vault e um `.env` injetado pelo gerenciador de implantação.

## Fallback sem demo ao vivo

Veja [presentation/screenshots/README.md](presentation/screenshots/README.md). A recomendação é capturar uma sequência normal/incidente/recuperação e manter as imagens em `presentation/captures/` (não versionadas por padrão). O roteiro completo está em [presentation/outline.md](presentation/outline.md).

## Limpeza

```bash
docker compose down -v
```

O `-v` remove os dados locais do PostgreSQL e é apropriado apenas para resetar o laboratório.

O banco da aplicação usa `timescale/timescaledb` sobre PostgreSQL 17 e cria a extensão TimescaleDB na primeira inicialização. Se você já tinha um volume criado antes dessa mudança, faça um reset do laboratório (`docker compose down -v`) antes de subir novamente.
