#!/usr/bin/env bash
set -euo pipefail
COMPOSE="/home/dev_taup/proyectos/quimex/docker-compose.yml"
python3 -c "
from pathlib import Path
p = Path('$COMPOSE')
t = p.read_text()
t = t.replace('DB_PORT: \"3309\"', 'DB_PORT: \"3306\"', 1)
p.write_text(t)
print('DB_PORT -> 3306')
"
cd /home/dev_taup/proyectos/quimex
docker compose up -d quimex-backend
for i in $(seq 1 30); do
  curl -sf http://127.0.0.1:5000/health >/dev/null 2>&1 && { echo Quimex OK; exit 0; }
  sleep 2
done
docker logs quimex-backend 2>&1 | tail -10
exit 1
