#!/usr/bin/env bash
set -euo pipefail
docker compose up -d --build
echo "API: http://localhost:5055 | Grafana: http://localhost:3000 | Jaeger: http://localhost:16686"
