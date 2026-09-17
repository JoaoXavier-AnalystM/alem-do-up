# OpenDockWatch separado

Stack independente para visualizar e controlar os containers Docker da VPS.

O OpenDockWatch não é iniciado pelo `docker-compose.yml` principal e não participa do ciclo de atualização da API, Grafana ou Zabbix.

## Configuração inicial

Na VPS:

```bash
cd /home/arq-sist/palestra/opendockwatch
cp .env.example .env
cp config/hosts.example.json config/hosts.json
```

No deploy principal, o OpenDockWatch reutiliza o usuário e a senha do Grafana
definidos no `.env` da VPS. A Action gera o hash automaticamente e preserva o
`SESSION_SECRET` entre os deploys.

Para uma inicialização manual, gere o hash da senha sem instalar Node.js na VPS:

```bash
docker run --rm darks1d3r/opendockwatch:2.7.0 node scripts/hash-password.js "SUA_SENHA"
```

Coloque o resultado em `AUTH_PASS_HASH` no arquivo `.env` e altere `SESSION_SECRET` para um valor aleatório longo.

Depois inicie:

```bash
chmod +x scripts/up.sh
./scripts/up.sh
```

Acesse `http://IP_DA_VPS:3001`.

O primeiro host configurado é o Docker local. O socket Docker permite leitura, logs, métricas e ações de start/stop/restart; por isso esta interface deve ficar protegida e não deve ser exposta diretamente à internet sem uma camada adicional de segurança.

Hosts remotos via SSH serão configurados em uma etapa posterior, usando uma chave dedicada do OpenDockWatch, sem reutilizar a chave de deploy do GitHub.
