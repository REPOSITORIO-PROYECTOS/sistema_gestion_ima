#!/usr/bin/env bash
# Backup + MySQL unificado (taup_mysql) + migración IMA / IMAPOS / Quimex / FacturacionIMA
set -euo pipefail

TS="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="/home/dev_taup/backups/mysql-unify-${TS}"
TAUP_MYSQL_DIR="/home/dev_taup/proyectos/taup-mysql"
UNIFIED_PORT=3309
ROOT_PW="${TAUP_MYSQL_ROOT_PASSWORD:-SistemaIMA123.}"
IMA_ROOT="SistemaIMA123."

log() { echo "[$(date +%H:%M:%S)] $*"; }

mkdir -p "$BACKUP_DIR"
log "Backup dir: $BACKUP_DIR"

dump_db() {
  local container="$1"
  local root_pw="$2"
  local db="$3"
  local out="$4"
  log "  dump $container/$db -> $(basename "$out")"
  docker exec "$container" mysqldump -uroot -p"$root_pw" \
    --single-transaction --routines --triggers --databases "$db" \
    > "$out"
}

log "=== 1/6 BACKUP ==="
dump_db sgi_db "$IMA_ROOT" ima_db "$BACKUP_DIR/ima_db.sql"
dump_db imapos_db "$IMA_ROOT" imapos_db "$BACKUP_DIR/imapos_db.sql"

# Quimex root desde .env del proyecto
QUIMEX_ENV="/home/dev_taup/proyectos/quimex/.env"
# shellcheck disable=SC1090
set -a && source "$QUIMEX_ENV" && set +a
QUIMEX_ROOT="${MYSQL_ROOT_PASSWORD:?Falta MYSQL_ROOT_PASSWORD en quimex/.env}"

dump_db quimex-db "$QUIMEX_ROOT" quimex_db "$BACKUP_DIR/quimex_db.sql"

# Facturacion (misma instancia quimex-db puerto 3307)
FACT_DB="facturacion_ima_restore_20260420"
if docker exec quimex-db mysql -uroot -p"$QUIMEX_ROOT" -N -e \
  "SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name='${FACT_DB}'" | grep -q '^1$'; then
  dump_db quimex-db "$QUIMEX_ROOT" "$FACT_DB" "$BACKUP_DIR/${FACT_DB}.sql"
else
  log "  skip facturacion DB (no existe en quimex-db)"
fi

tar -czf "${BACKUP_DIR}.tar.gz" -C "$(dirname "$BACKUP_DIR")" "$(basename "$BACKUP_DIR")"
log "Backup comprimido: ${BACKUP_DIR}.tar.gz"

log "=== 2/6 MySQL unificado ==="
mkdir -p "$TAUP_MYSQL_DIR"
cat > "$TAUP_MYSQL_DIR/.env" <<EOF
MYSQL_ROOT_PASSWORD=${ROOT_PW}
TZ=America/Argentina/Buenos_Aires
EOF

cat > "$TAUP_MYSQL_DIR/docker-compose.yml" <<'EOF'
services:
  taup_mysql:
    image: mysql:8.0
    container_name: taup_mysql
    restart: unless-stopped
    ports:
      - "127.0.0.1:3309:3306"
    env_file:
      - .env
    volumes:
      - taup_mysql_data:/var/lib/mysql
    command:
      - --character-set-server=utf8mb4
      - --collation-server=utf8mb4_unicode_ci
      - --innodb_buffer_pool_size=512M
      - --max_connections=200
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 10
      start_period: 40s

volumes:
  taup_mysql_data:
EOF

cd "$TAUP_MYSQL_DIR"
docker compose up -d
log "Esperando taup_mysql (healthcheck)..."
for i in $(seq 1 60); do
  status="$(docker inspect taup_mysql --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}unknown{{end}}' 2>/dev/null || echo unknown)"
  if [[ "$status" == "healthy" ]]; then
    if docker exec taup_mysql mysql -uroot -p"$ROOT_PW" -N -e "SELECT 1" >/dev/null 2>&1; then
      log "  taup_mysql listo (${i}s)"
      break
    fi
  fi
  if [[ "$i" -eq 60 ]]; then
    log "ERROR: taup_mysql no quedó healthy a tiempo (status=$status)"
    exit 1
  fi
  sleep 2
done

log "=== 3/6 IMPORT ==="
for sql in "$BACKUP_DIR"/*.sql; do
  [[ -f "$sql" ]] || continue
  log "  import $(basename "$sql")"
  docker exec -i taup_mysql mysql -uroot -p"$ROOT_PW" < "$sql"
done

log "=== 4/6 USUARIOS ==="
IMA_USER="gestion_user"
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

# Quimex backend: conectar al MySQL del host (puente docker)
QUIMEX_COMPOSE="/home/dev_taup/proyectos/quimex/docker-compose.yml"
if grep -q 'DB_HOST: quimex-db' "$QUIMEX_COMPOSE"; then
  sed -i 's/DB_HOST: quimex-db/DB_HOST: 172.17.0.1/' "$QUIMEX_COMPOSE"
  sed -i "s/DB_PORT: \"3306\"/DB_PORT: \"${UNIFIED_PORT}\"/" "$QUIMEX_COMPOSE"
fi

log "=== 6/6 REINICIAR + VERIFICAR ==="
sudo -u dev_taup pm2 start gestion-ima-api gestion-ima-sync IMAPOS_api IMAPOS_sheets_sync facturacion-backend-dev 2>/dev/null || \
  sudo -u dev_taup pm2 restart gestion-ima-api gestion-ima-sync IMAPOS_api IMAPOS_sheets_sync facturacion-backend-dev

cd /home/dev_taup/proyectos/quimex && docker compose up -d quimex-backend quimex-frontend

sleep 10
docker exec taup_mysql mysql -uroot -p"$ROOT_PW" -N -e "SHOW DATABASES;" | grep -E 'ima_db|imapos|quimex|facturacion' || true

curl -sf http://127.0.0.1:8011/api/health && echo " <- IMA OK" || echo "IMA FAIL"
curl -sf http://127.0.0.1:8033/api/health && echo " <- IMAPOS OK" || echo "IMAPOS FAIL"
curl -sf http://127.0.0.1:5000/api/health 2>/dev/null && echo " <- Quimex OK" || curl -sf -o /dev/null -w "Quimex HTTP %{http_code}\n" http://127.0.0.1:5000/ || echo "Quimex check manual"

log "MySQL unificado: 127.0.0.1:${UNIFIED_PORT} (taup_mysql)"
log "Instancias viejas (sgi_db, imapos_db, quimex-db) siguen apagadas de apps pero contenedores existen."
log "Si todo OK 24h, apagar: docker stop sgi_db imapos_db quimex-db"
log "Rollback: restaurar .env DB_PORT anterior + dumps en ${BACKUP_DIR}.tar.gz"
