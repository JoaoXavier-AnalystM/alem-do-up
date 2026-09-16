# Zabbix — disponibilidade e infraestrutura

O Zabbix faz parte do Compose principal. Suba-o com:

```bash
docker compose --profile zabbix up -d
```

Abra `http://localhost:8081` e use a credencial administrativa configurada no primeiro acesso da sua VM; ela não é documentada nem armazenada neste repositório. Crie o host `nginx` com interface DNS `nginx:80` e itens HTTP para `/health` e `/checkout`. O primeiro pode continuar verde durante o incidente; o segundo expõe a saúde da jornada.

O Agent 2 desta demo não usa `privileged`, `pid: host` nem `/var/run/docker.sock`. Para monitoramento de host, crie uma variante explícita e revisada pela equipe de segurança, em vez de ampliar o privilégio do stack padrão.
