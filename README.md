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
# Preencha os segredos no .env sem versioná-lo.
chmod +x scripts/*.sh
docker compose up -d --build
./scripts/smoke.sh
```

## Roteiro da demonstração

```bash
./scripts/normal.sh
./scripts/incident.sh
./scripts/load.sh
./scripts/recover.sh
```

Observe durante o roteiro:

- Aplicação: <http://localhost:8080>
- Grafana: <http://localhost:3000>
- Prometheus: <http://localhost:9090>
- Jaeger: <http://localhost:16686>

Arquitetura detalhada: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

O workflow de deploy usa secrets do GitHub e não publica informações da VPS no
código. A configuração operacional completa fica fora do material público.

## Limpeza

```bash
docker compose down -v
```
