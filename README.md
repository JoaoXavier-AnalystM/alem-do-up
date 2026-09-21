# Seu sistema está UP. Mas ele está saudável?

Laboratório de observabilidade para uma palestra.

A demonstração mostra uma aplicação que continua tecnicamente disponível, mas
fica degradada quando o pool de conexões com o PostgreSQL é ocupado:

```text
Usuário → Nginx → Checkout API → PostgreSQL
                    ↓
       métricas · logs · traces · alertas
```

## O que existe

- API FastAPI com checkout, healthcheck e métricas Prometheus.
- PostgreSQL/TimescaleDB com pool de conexões controlado.
- Nginx, Prometheus, Grafana, Loki, Jaeger e OpenTelemetry.
- Zabbix opcional para comparar disponibilidade com saúde real.
- OpenDockWatch separado para acompanhar os containers Docker da VPS.
- Scripts shell para iniciar, provocar, observar e recuperar o incidente.

## O que vamos testar e comprovar

1. O sistema inicia e responde normalmente.
2. O `/health` continua verde no começo do problema.
3. O checkout fica mais lento e começa a falhar.
4. O pool mostra conexões ocupadas e requisições esperando.
5. Métricas, logs e traces apontam para a mesma causa.
6. Ao liberar as conexões, a aplicação se recupera.

## Executar localmente ou na VPS

Pré-requisitos: Docker Compose e, para carga, `k6` ou `hey`.

```bash
cp .env.example .env
# Os valores do exemplo são apenas para o laboratório.
chmod +x scripts/*.sh
./scripts/up.sh
./scripts/smoke.sh
```

## Roteiro da demonstração

### Roteiro da palestra

1. Mostre que a API, o banco e o monitoramento estão verdes.
2. Execute um checkout normal e confirme a resposta rápida.
3. Ative o incidente e gere carga com `K6_INCIDENT=true K6_VUS=50 K6_DURATION=5m ./scripts/load.sh`.
4. Compare o `/health` com o `/checkout`: o processo pode continuar online enquanto a jornada degrada.
5. No Grafana, correlacione latência, pool e erros; no Loki, procure `pool_exhausted`; no Jaeger, observe a espera no banco.
6. Recupere o sistema e confirme que os sinais voltam ao normal.

O ponto principal da demonstração é separar disponibilidade técnica de saúde da experiência do usuário.

```bash
./scripts/normal.sh
./scripts/incident.sh
./scripts/load.sh
./scripts/recover.sh
```

Observe durante o roteiro. A interface de apresentação concentra os controles e
os indicadores em uma tela:

- Interface da aplicação: <http://localhost:5055>
- Índice técnico da API: <http://localhost:5055/checkout-api>
- Grafana: <http://localhost:3000>
- Prometheus: <http://localhost:9090>
- Jaeger: <http://localhost:16686>
- OpenDockWatch separado: <http://localhost:3001>

O caminho da interface é definido por `APP_UI_PREFIX` no `.env` e usa `demo`
por enquanto. Assim, ele poderá virar `porteira-tech` sem alterar a aplicação.

O OpenDockWatch possui Compose, configuração e ciclo de vida próprios em
[opendockwatch/](opendockwatch/). Ele não é iniciado pelo stack principal.

Arquitetura detalhada: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

O workflow de deploy usa secrets do GitHub e não publica informações da VPS no
código. No laboratório, ele copia o `.env.example` preenchido para `.env` em
todo deploy. Não use essas credenciais de demonstração em produção.

## Limpeza

```bash
docker compose down -v
```
