# syntax=docker/dockerfile:1.7
FROM grafana/grafana-oss:12.3.1-security-01

USER root

RUN mkdir -p /usr/share/grafana/plugins \
    && /usr/share/grafana/bin/grafana cli --pluginsDir /usr/share/grafana/plugins plugins install alexanderzobnin-zabbix-app 6.0.3 \
    && /usr/share/grafana/bin/grafana cli --pluginsDir /usr/share/grafana/plugins plugins install gapit-htmlgraphics-panel 2.2.3 \
    && chown -R grafana:root /usr/share/grafana/plugins

ENV GF_PATHS_PLUGINS=/usr/share/grafana/plugins

USER grafana
