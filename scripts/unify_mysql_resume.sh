#!/usr/bin/env bash
# Retoma unificación MySQL desde backup existente (pasos 3-6)
set -euo pipefail

BACKUP_DIR="${1:?Uso: unify_mysql_resume.sh /home/dev_taup/backups/mysql-unify-YYYYMMDD_HHMMSS}"
UNIFIED_PORT=3309
ROOT_PW="${TAUP_MYSQL_ROOT_PASSWORD:-SistemaIMA123.}"
IMA_USER="gestion_user"
QUIMEX_ENV="/home/dev_taup/proyectos/quimex/.env"
FACT_DB="facturacion_ima_restore_20260420"
QUIMEX_COMPOSE="/home/dev_taup/proyectos/quimex/docker-compose.yml"

log() { echo "[$(date +%H:%M:%S)] $*"; }

if [[ ! -d "$BACKUP_DIR" ]]; then
  echo "No existe backup dir: $BACKUP_DIR"
  exit 1
fi

log "Esperando taup_mysql healthy..."
for i in $(seq 1 30); do
  status="$(docker inspect taup_mysql --format='{{.State.Health.Status}}' 2>/dev/null || echo unknown)"
  [[ "$status" == "healthy" ]] && break
  sleep 2
done

log "=== 3/6 IMPORT (resume) ==="
for sql in "$BACKUP_DIR"/*.sql; do
  [[ -f "$sql" ]] || continue
  log "  import $(basename "$sql")"
  docker exec -i taup_mysql mysql -uroot -p"$ROOT_PW" < "$sql"
done

log "=== 4/6 USUARIOS ==="
IMA_PASS="$(grep '^DB_PASSWORD=' /home/dev_taup/proyectos/sistema_gestion_ima/.env | cut -d= -f2-)"
QUIMEX_PASS="$(grep '^MYSQL_PASSWORD=' "$QUIMEX_ENV" | cut -d= -f2-)"

docker exec -i taup_mysql mysql -uroot -p"$ROOT_PW" <<SQL
CREATE USER IF NOT EXISTS '${IMA_USER}'@'%' IDENTIFIED BY '${IMA_PASS}';
CREATE USER IF NOT EXISTS '${IMA_USER}'@'localhost' IDENTIFIED BY '${IMA_PASS}';
GRANT ALL PRIVILEGES ON ima_db.* TO '${IMA_USER}'@'%';
GRANT ALL PRIVILEGES ON ima_db.* TO '${IMA_USER}'@'localhost';
GRANT ALL PRIVILEGES ON imapos_db.* TO '${IMA_USER}'@'%';
GRANT ALL PRIVILEGES ON imapos_db.* TO '${IMA_USER}'@'localhost';
GRANT ALL PRIVILEGES ON \`${FACT_DB}\`.* TO '${IMA_USER}'@'%';
GRANT ALL PRIVILEGES ON \`${FACT_DB}\`.* TO '${IMA_USER}'@'localhost';
CREATE USER IF NOT EXISTS 'quimex'@'%' IDENTIFIED BY '${QUIMEX_PASS}';
GRANT ALL PRIVILEGES ON quimex_db.* TO 'quimex'@'%';
ALTER USER 'quimex'@'%' IDENTIFIED BY '${QUIMEX_PASS}';
FLUSH PRIVILEGES;
SQL

log "=== 5/6 DETENER APPS + ACTUALIZAR CONFIG ==="
sudo -u dev_taup pm2 stop gestion-ima-api gestion-ima-sync IMAPOS_api IMAPOS_sheets_sync facturacion-backend-dev 2>/dev/null || true
cd /home/dev_taup/proyectos/quimex && docker compose stop quimex-backend quimex-frontend 2>/dev/null || true

sed -i "s/^DB_PORT=.*/DB_PORT=${UNIFIED_PORT}/" /home/dev_taup/proyectos/sistema_gestion_ima/.env
sed -i "s/^DB_NAME=.*/DB_NAME=ima_db/" /home/dev_taup/proyectos/sistema_gestion_ima/.env
if [[ -f /home/dev_taup/proyectos/sistema_gestion_ima/back/.env ]]; then
  sed -i "s/^DB_PORT=.*/DB_PORT=${UNIFIED_PORT}/" /home/dev_taup/proyectos/sistema_gestion_ima/back/.env
  sed -i "s/^DB_NAME=.*/DB_NAME=ima_db/" /home/dev_taup/proyectos/sistema_gestion_ima/back/.env
fi
sed -i "s/^DB_PORT=.*/DB_PORT=${UNIFIED_PORT}/" /home/dev_taup/proyectos/imapos.2.0/.env
sed -i "s/^DB_PORT=.*/DB_PORT=${UNIFIED_PORT}/" /home/dev_taup/proyectos/FacturacionIMA/.env
sed -i "s/^NEW_DB_PORT=.*/NEW_DB_PORT=${UNIFIED_PORT}/" /home/dev_taup/proyectos/FacturacionIMA/.env 2>/dev/null || true

if grep -q 'DB_HOST: quimex-db' "$QUIMEX_COMPOSE"; then
  sed -i 's/DB_HOST: quimex-db/DB_HOST: 172.17.0.1/' "$QUIMEX_COMPOSE"
  sed -i "s/DB_PORT: \"3306\"/DB_PORT: \"${UNIFIED_PORT}\"/" "$QUIMEX_COMPOSE"
fi

log "=== 6/6 REINICIAR + VERIFICAR ==="
sudo -u dev_taup pm2 start gestion-ima-api gestion-ima-sync IMAPOS_api IMAPOS_sheets_sync facturacion-backend-dev 2>/dev/null || \
  sudo -u dev_taup pm2 restart gestion-ima-api gestion-ima-sync IMAPOS_api IMAPOS_sheets_sync facturacion-backend-dev

cd /home/dev_taup/proyectos/quimex && docker compose up -d quimex-backend quimex-frontend

sleep 12
docker exec taup_mysql mysql -uroot -p"$ROOT_PW" -N -e "SHOW DATABASES;" | grep -E 'ima_db|imapos|quimex|facturacion' || true

curl -sf http://127.0.0.1:8011/api/health && echo " <- IMA OK" || echo "IMA FAIL"
curl -sf http://127.0.0.1:8033/api/health && echo " <- IMAPOS OK" || echo "IMAPOS FAIL"
curl -sf http://127.0.0.1:5000/api/health 2>/dev/null && echo " <- Quimex OK" || curl -sf -o /dev/null -w "Quimex HTTP %{http_code}\n" http://127.0.0.1:5000/ || echo "Quimex check manual"
curl -sf http://127.0.0.1:8012/api/health 2>/dev/null && echo " <- Facturacion OK" || echo "Facturacion check manual"

log "MySQL unificado: 127.0.0.1:${UNIFIED_PORT} (taup_mysql)"
log "Rollback: restaurar DB_PORT anterior + dumps en ${BACKUP_DIR}.tar.gz"
