# Roteiro da palestra

## 1 — Tudo verde (2 min)

Mostrar `/health` 200 e o painel. Pergunta: “O sistema está saudável?” A resposta esperada é “parece que sim”.

## 2 — A reclamação (2 min)

Rodar carga e narrar: “usuários dizem que finalizar a compra demora”. CPU e memória ainda não explicam o problema.

## 3 — Latência (4 min)

No painel, destacar HTTP p95. Explicar percentil: não é a média; mostra a cauda que afeta quem está esperando.

## 4 — Conexões (4 min)

Mostrar `in_use`, `waiting` e `size`. O pool chegou ao limite. A API ainda está viva, mas solicitações aguardam.

## 5 — Logs (3 min)

Abrir Loki/Grafana e buscar `pool_exhausted`. Ler a sequência: timeout → erro de checkout → reclamação.

## 6 — Trace (4 min)

Abrir Jaeger, selecionar `checkout-api` e mostrar PostgreSQL ocupando a maior parte do span.

## 7 — RCA e melhoria (5 min)

RCA: conexões ficam ocupadas por operações lentas; o pool tem capacidade finita; health básico não mede jornada. Melhorias: timeout explícito, pool bem dimensionado, métricas de espera, alerta de p95/error rate e tracing.

## Fechamento

> Não basta saber se está funcionando. Precisamos conseguir entender por que não está funcionando como deveria.

