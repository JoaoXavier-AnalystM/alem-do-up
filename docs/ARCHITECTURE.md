# Arquitetura do Além do UP

Documento de fronteira para os agentes Atlas, Dock, Pulse, Forge, Chaos e
Sentinel. Atlas define contratos; cada agente implementa somente seu domínio.

## Escopo atual

```text
usuário local/k6
        |
        v
  host:APP_PORT (5055)
        |
        v
      Nginx ---------------> API FastAPI ---------------> PostgreSQL
        |                         |                          |
        |                         +--> /metrics <--- Prometheus
        |                         +--> OTLP --> Collector --> Jaeger
        |                         +--> stdout --> Promtail --> Loki
        |
        +--> Grafana (consulta Prometheus, Loki, Jaeger e PostgreSQL)

usuário público --> Cloudflare Tunnel --> portas do host
operador --------> OpenDockWatch --> Docker socket do host
```

O caminho crítico é:

```text
usuário -> Nginx -> FastAPI -> pool asyncpg -> PostgreSQL
```

`api --ready -> nginx` representa estado alvo. Compose atual usa `/health` no
healthcheck da API; Dock e Forge devem migrar para `/readyz` conforme contrato.

Cloudflare, Grafana, Prometheus, Loki, Jaeger, Zabbix e OpenDockWatch ficam
fora do caminho de resposta do checkout. Falha de observabilidade não pode
impedir tráfego de negócio.

## Limites de serviço

| Componente | Responsabilidade | Não deve assumir |
| --- | --- | --- |
| Cloudflare Tunnel | Publicar portas do host | Saúde interna ou lógica de negócio |
| Nginx | Entrada HTTP, proxy e access log | Estado do incidente ou acesso direto ao banco |
| FastAPI | Contrato HTTP de checkout, saúde e métricas | Persistência fora do PostgreSQL; controle demo público |
| Demo controller | Ativar cenários artificiais | Fazer parte da jornada pública |
| PostgreSQL | Estado persistente e execução SQL | Métricas de usuário ou controle de carga |
| Prometheus | Coletar séries e avaliar regras | Ser prova única da jornada pública |
| Promtail/Loki | Coletar e consultar logs | Decidir disponibilidade |
| OpenTelemetry/Jaeger | Transportar e consultar traces | Ser dependência síncrona da API |
| Grafana | Apresentar sinais correlacionados | Ser requisito para servir checkout |
| Zabbix | Disponibilidade/infra opcional | Ser dependência do stack principal |
| OpenDockWatch | Operar containers do host | Participar do request path |

FastAPI atualmente também serve UI estática e endpoints de demonstração. Essa
mistura é aceita somente como estado transitório de laboratório. O controlador
de demonstração deve ser protegido ou isolado antes de qualquer exposição
pública.

## Mapa de dependências

`A -> B` significa dependência de runtime de B em A.

```text
db --healthy -> api --ready -> nginx

api -> otel-collector -> jaeger
api <- prometheus
loki <- promtail <- Docker logs/socket
prometheus + loki + jaeger + db -> grafana

zabbix-db --healthy -> zabbix-server -> zabbix-agent2
zabbix-db --healthy + zabbix-server -> zabbix-web

Cloudflare Tunnel -> host ports -> nginx/grafana/zabbix/jaeger/OpenDockWatch
OpenDockWatch -> Docker socket
```

Dependências de observabilidade são assíncronas ou de consulta. API não pode
falhar requisições porque Collector, Jaeger, Prometheus, Loki ou Grafana estão
indisponíveis.

## Gates entre agentes

1. Atlas: contratos, fronteiras e decisões deste documento.
2. Dock: Compose, readiness, bootstrap, imagens e persistência.
3. Pulse: métricas, logs, traces, probes e dashboards.
4. Forge: comportamento FastAPI, pool e erros HTTP.
5. Chaos: carga, saturação e recuperação determinísticas.
6. Sentinel: integração, QA e documentação final.

Dock consome as interfaces de saúde definidas em
[ARCHITECTURE_CONTRACTS.md](ARCHITECTURE_CONTRACTS.md). Pulse e Forge não
devem inventar endpoints ou nomes de métricas fora daquele contrato.

## Decisões arquiteturais

- Liveness, readiness e saúde de negócio são sinais distintos.
- Pool asyncpg é recurso da aplicação; PostgreSQL é dependência de dados.
- Saturação artificial deve ser identificada como cenário demo, não como falha
  espontânea de PostgreSQL.
- `/demo/*` é superfície administrativa, não superfície pública.
- Nginx é único entrypoint HTTP local do stack.
- Cloudflare é camada de publicação, não dependência interna.
- Zabbix local e Zabbix remoto são configurações diferentes, selecionadas por
  ambiente.
- Estado demo em memória limita escala horizontal. Remover `container_name` e
  escalar API exige mover estado demo para controlador dedicado ou store comum.
- Datasources e exporters podem consultar o banco, mas API não consulta
  observabilidade para responder checkout.

## Entregas Atlas

- [#3 Contratos de saúde e probes](https://github.com/JoaoXavier-AnalystM/alem-do-up/issues/3)
- [#4 Isolar controle de demonstração](https://github.com/JoaoXavier-AnalystM/alem-do-up/issues/4)
- [#12 Telemetria real do pool e banco](https://github.com/JoaoXavier-AnalystM/alem-do-up/issues/12)
- [#14 Grafo de dependências e readiness](https://github.com/JoaoXavier-AnalystM/alem-do-up/issues/14)
- [#15 Desacoplar Zabbix e Cloudflare](https://github.com/JoaoXavier-AnalystM/alem-do-up/issues/15)

Contratos detalhados: [ARCHITECTURE_CONTRACTS.md](ARCHITECTURE_CONTRACTS.md).
