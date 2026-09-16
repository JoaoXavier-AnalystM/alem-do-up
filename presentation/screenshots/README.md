# Plano de evidências visuais

Para não depender de uma demo ao vivo, capture quatro telas por estado:

1. Aplicação: `/health` e `/checkout`.
2. Grafana: p95 + pool + errors.
3. Loki: busca por `pool_exhausted`.
4. Jaeger: trace com PostgreSQL dominante.

Sequência recomendada: `01-normal`, `02-complaint`, `03-incident-pool`, `04-logs`, `05-trace`, `06-recovered`. Grave também um vídeo curto de 30–60s mostrando os quatro comandos do README. As capturas ficam em `presentation/captures/`, que é ignorada para evitar imagens grandes no repositório.
