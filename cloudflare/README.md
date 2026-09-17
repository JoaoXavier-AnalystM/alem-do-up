# Cloudflare Tunnel

Stack separada para manter a conexão da VPS com o Cloudflare.

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
