FROM grafana/grafana-oss:12.3.1-security-01

USER root
RUN grafana cli plugins install alexanderzobnin-zabbix-app 6.0.3
USER grafana
