# Checklist da apresentacao

Use este roteiro depois do deploy. Envie um print por etapa ou um conjunto de prints que cubra os itens indicados.

## 1. Estado inicial

- Abra `https://aplicacao-ps.joaoxavier.app.br`.
- Confirme o badge `SISTEMA NORMAL`.
- Confirme `Saude tecnica: OK`.
- Confirme `Jornada do usuario: OK`.
- Envie um print da tela inicial.

## 2. Acessos publicados

Abra os quatro atalhos da aplicacao e confirme que carregam:

- `https://grafana-ps.joaoxavier.app.br`
- `https://jaeger-ps.joaoxavier.app.br`
- `https://opendock-ps.joaoxavier.app.br`
- `https://zabbix-ps.joaoxavier.app.br`

Envie um print da tela de ferramentas ou dos acessos funcionando.

## 3. Pressao controlada

- Clique em `Provocar incidente`.
- Observe o destaque das etapas `Pressao`, `Sintoma` e `Evidencia`.
- Confirme que a API continua acessivel.
- Envie um print mostrando o estado `INCIDENTE ATIVO`.

## 4. Carga k6

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

## 5. Grafana

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

## 6. Logs e traces

No Loki, procure por:

```text
{container="api-up"} |= "pool"
```

No Jaeger, procure pelo servico `checkout-api` e abra um trace de `/checkout`.

Envie um print de um log de `pool_exhausted` e de um trace mostrando a chamada ao banco.

## 7. Recuperacao

- Clique em `Voltar ao normal` ou execute `./scripts/recover.sh`.
- Aguarde o pool esvaziar.
- Confirme que `Saude tecnica` e `Jornada do usuario` voltaram ao normal.
- Confirme que os paineis deixam de apresentar novos erros.

Envie o print final da recuperacao.

## Resultado esperado

Ao final, os prints devem comprovar a mensagem da palestra:

> A infraestrutura pode estar online e verde enquanto a jornada do usuario ja esta degradada.
