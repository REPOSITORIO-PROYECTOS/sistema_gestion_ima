#!/usr/bin/env bash
set -euo pipefail

COMPOSE="/home/dev_taup/proyectos/quimex/docker-compose.yml"

python3 <<'PY'
from pathlib import Path

path = Path("/home/dev_taup/proyectos/quimex/docker-compose.yml")
text = path.read_text()

needle = '''    networks:
      - quimex
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]'''

replacement = '''    networks:
      - quimex
      - taup_mysql
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]'''

if needle in text:
    text = text.replace(needle, replacement, 1)
elif "      - taup_mysql" not in text:
    raise SystemExit("No se encontró bloque quimex-backend para parchear")

if "taup_mysql:" not in text:
    text = text.replace(
        "networks:\n  quimex:\n    driver: bridge\n",
        "networks:\n  quimex:\n    driver: bridge\n  taup_mysql:\n    external: true\n    name: taup-mysql_default\n",
    )

path.write_text(text)
print("compose patched")
PY

grep -A3 'DB_HOST' "$COMPOSE" | head -4
grep -A4 'quimex-backend:' "$COMPOSE" | tail -3 || true

cd /home/dev_taup/proyectos/quimex
docker compose up -d quimex-backend

for i in $(seq 1 45); do
  if curl -sf http://127.0.0.1:5000/health >/dev/null 2>&1; then
    echo "Quimex /health OK"
    exit 0
  fi
  sleep 2
done

docker logs quimex-backend 2>&1 | tail -20
exit 1
