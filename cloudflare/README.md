# Cloudflare Tunnel

Stack separada para manter a conexão da VPS com o Cloudflare.

O token do Tunnel não fica no repositório. O workflow `Deploy Cloudflare
Tunnel` recebe `CLOUDFLARE_TUNNEL_TOKEN` dos secrets do GitHub e cria o
`cloudflare/.env` somente na VPS.

## Configuração na VPS

```bash
cd /home/arq-sist/palestra/cloudflare
cp .env.example .env
vi .env
docker compose up -d
```

O serviço usa `restart: unless-stopped`: ele volta automaticamente após
reinício da VPS ou caso o processo do container seja encerrado. Para parar
manualmente, use `docker compose stop`.

As Published Application Routes continuam sendo configuradas no Tunnel do
Cloudflare. O container apenas mantém o Tunnel conectado e aplica as rotas já
associadas ao token.

## Secrets do GitHub

Já utilizados pelo workflow:

- `VPS_HOST`
- `VPS_PORT`
- `VPS_USER`
- `VPS_APP_DIR`
- `VPS_SSH_KEY`
- `CLOUDFLARE_TUNNEL_TOKEN`

Para o cadastro automático de DNS e rotas, serão adicionados depois:

- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ACCOUNT_ID`
- `CLOUDFLARE_TUNNEL_ID`
- `CLOUDFLARE_ZONE_ID`
- `CLOUDFLARE_DOMAIN`
- `CLOUDFLARE_ORIGIN_HOST`

O workflow cria automaticamente:

- `aplicacao-ps.<CLOUDFLARE_DOMAIN>` → API/interface na porta `5055`;
- `grafana-ps.<CLOUDFLARE_DOMAIN>` → Grafana na porta `3000`.

Os CNAMEs apontam para `<CLOUDFLARE_TUNNEL_ID>.cfargotunnel.com`.
