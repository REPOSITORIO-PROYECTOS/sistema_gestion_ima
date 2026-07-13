#!/usr/bin/env bash
set -euo pipefail
echo "=== HEALTH CHECKS ==="
curl -sf -o /dev/null -w "IMA health: %{http_code}\n" http://127.0.0.1:8011/api/health || echo "IMA health: FAIL"
curl -sf -o /dev/null -w "IMA articulos: %{http_code}\n" "http://127.0.0.1:8011/api/articulos/obtener?pagina=1&limite=1" || echo "IMA articulos: FAIL"
curl -sf -o /dev/null -w "IMAPOS: %{http_code}\n" http://127.0.0.1:8033/api/health || echo "IMAPOS: FAIL"
curl -sf -o /dev/null -w "Quimex: %{http_code}\n" http://127.0.0.1:5000/health || echo "Quimex: FAIL"
curl -sf -o /dev/null -w "Facturacion: %{http_code}\n" http://127.0.0.1:8012/healthz || echo "Facturacion: FAIL"
echo "=== DOCKER ==="
docker ps --format "{{.Names}} {{.Status}}" | grep -E "taup_mysql|quimex" || true
echo "=== PM2 ==="
sudo -u dev_taup pm2 list | grep -E "gestion-ima|IMAPOS|factur" || true
