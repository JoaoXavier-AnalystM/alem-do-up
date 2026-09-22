# Checklist da apresentacao

Use este roteiro depois do deploy. Envie um print por etapa ou um conjunto de prints que cubra os itens indicados.

## 1. Duas telas

- Abra `/` para a visão macro do apresentador.
- Abra `/comprar` em outra aba para os participantes usarem o checkout.
- Comece em `Normal` e confirme `OK` nas quatro etapas.
- Na tela `/comprar`, envie cadastros preenchendo nome, idade e cargo/profissão.
- Use a sequência: 5 cadastros para degradar, 10 para problema crítico e 15 para offline.

Os limiares podem ser ajustados no `.env` por `DEMO_DEGRADED_AFTER`,
`DEMO_CRITICAL_AFTER` e `DEMO_OFFLINE_AFTER`; depois, recrie o serviço da API.

## 2. Estado inicial

- Abra `https://aplicacao-ps.joaoxavier.app.br`.
- Confirme o badge `SISTEMA NORMAL`.
- Confirme `Saude tecnica: OK`.
- Confirme `Jornada do usuario: OK`.
- Envie um print da tela inicial.

## 3. Acessos publicados

Abra os quatro atalhos da aplicacao e confirme que carregam:

- `https://grafana-ps.joaoxavier.app.br`
- `https://jaeger-ps.joaoxavier.app.br`
- `https://opendock-ps.joaoxavier.app.br`
- `https://zabbix-ps.joaoxavier.app.br`

Envie um print da tela de ferramentas ou dos acessos funcionando.

## 4. Pressao controlada

- Na visão macro, clique em `Degradar` e use `/comprar` para mostrar a lentidão.
- Depois clique em `Saturar` e observe `INCIDENTE` e as falhas no checkout público.
- Para a narrativa completa, use `Iniciar progressão`: `OK` → `DEGRADADO` → `INCIDENTE` → `OFFLINE`.
- A página `/` continua acessível em `OFFLINE`; apenas o negócio deixa de concluir.

## 5. Carga k6

Na VPS, execute:

```bash
K6_INCIDENT=true K6_VUS=50 K6_DURATION=5m K6_TEST_ID=checkout-heavy ./scripts/load.sh
```

Esse comando usa `localhost:5055` e mede principalmente a aplicacao, sem atravessar o Cloudflare.
Como a VPS esta na OCI em Ashburn, a latencia vista pelo navegador no Brasil pode ser maior.
Para medir a experiencia real pelo DNS publico, execute uma segunda rodada:

```bash
BASE_URL=https://aplicacao-ps.joaoxavier.app.br \
K6_INCIDENT=true K6_VUS=20 K6_DURATION=2m K6_TEST_ID=checkout-public \
./scripts/load.sh
```

Compare a variacao entre as rodadas, e nao apenas o valor absoluto. A primeira isola a aplicacao;
a segunda representa a jornada do usuario atraves do Cloudflare e da rede ate Ashburn.

Confirme no terminal:

- 50 VUs;
- duracao de 5 minutos;
- threshold avaliado;
- percentual de erros e p95.

Envie o print do resumo final do k6.

## 6. Grafana

No dashboard `Checkout - UP mas nao saudavel`, confirme:

- p95 do checkout;
- pool em uso;
- requisicoes aguardando;
- erros de checkout;
- health da API.

No dashboard `Carga k6 - checkout`, confirme:

- requisicoes por segundo;
- falhas HTTP;
- VUs;
- checks;
- latencia HTTP;
- duracao das iteracoes.

Envie os prints dos dois dashboards durante a carga.

## 7. Logs e traces

No Loki, procure por:

```text
{container="api-up"} |= "pool"
```

No Jaeger, procure pelo serviço `checkout-api` e abra um trace de `/checkout`.

Envie um print de um log de `pool_exhausted` e de um trace mostrando a chamada ao banco.

## 8. Recuperacao

- Clique em `Normal` ou execute `./scripts/recover.sh`.
- Aguarde o pool esvaziar.
- Confirme que `Saude tecnica` e `Jornada do usuario` voltaram ao normal.
- Confirme que os paineis deixam de apresentar novos erros.

Envie o print final da recuperacao.

## Resultado esperado

Ao final, os prints devem comprovar a mensagem da palestra:

> A infraestrutura pode estar online e verde enquanto a jornada do usuario ja esta degradada.
