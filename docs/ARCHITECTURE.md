# Arquitetura

```text
                         ┌──────────────┐
hey / k6 ───────────────>│ Nginx :8080  │
                         └──────┬───────┘
                                v
                         ┌──────────────┐       ┌────────────┐
                         │ Checkout API │──────>│ PostgreSQL │
                         └──┬────┬───┬──┘       └────────────┘
                            │    │   │
                 metrics ───┘    │   └── logs → Loki
                 traces ─────────┘       spans → Jaeger
```

O ponto didático é que `/health` verifica processo e contrato básico, não a experiência completa de checkout. Durante o incidente ele pode retornar 200 no início, enquanto o p95 e `pool_waiting` já contam a história real.
