#!/usr/bin/env bash
# Renombra gestion_ima_db -> nombre único por app (prep unificación MySQL).
set -euo pipefail

ROOT_PW="${MYSQL_ROOT_PASSWORD:-SistemaIMA123.}"

rename_database() {
  local container="$1"
  local old_db="$2"
  local new_db="$3"

  echo "=== $container: $old_db -> $new_db ==="

  local exists
  exists=$(docker exec "$container" mysql -uroot -p"$ROOT_PW" -N -e \
    "SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name='${new_db}'")

  if [[ "$exists" != "0" ]]; then
    echo "  DB ${new_db} ya existe, omitiendo rename."
    return 0
  fi

  local tables
  tables=$(docker exec "$container" mysql -uroot -p"$ROOT_PW" -N -e \
    "SELECT table_name FROM information_schema.tables WHERE table_schema='${old_db}' ORDER BY table_name")

  if [[ -z "$tables" ]]; then
    echo "  No hay tablas en ${old_db}, omitiendo."
    return 0
  fi

  docker exec "$container" mysql -uroot -p"$ROOT_PW" -e \
    "CREATE DATABASE \`${new_db}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

  local rename_list=""
  while IFS= read -r t; do
    [[ -z "$t" ]] && continue
    rename_list+="\`${old_db}\`.\`${t}\` TO \`${new_db}\`.\`${t}\`,"
  done <<< "$tables"
  rename_list="${rename_list%,}"

  docker exec "$container" mysql -uroot -p"$ROOT_PW" -e "RENAME TABLE ${rename_list};"
  docker exec "$container" mysql -uroot -p"$ROOT_PW" -e "DROP DATABASE \`${old_db}\`;"
  docker exec "$container" mysql -uroot -p"$ROOT_PW" -e \
    "GRANT ALL PRIVILEGES ON \`${new_db}\`.* TO 'gestion_user'@'%'; FLUSH PRIVILEGES;"

  echo "  OK: ${new_db} ($(echo "$tables" | wc -l) tablas)"
}

echo "Deteniendo apps que escriben en DB..."
sudo -u dev_taup pm2 stop gestion-ima-api gestion-ima-sync IMAPOS_api IMAPOS_sheets_sync 2>/dev/null || true

rename_database "sgi_db" "gestion_ima_db" "ima_db"
rename_database "imapos_db" "gestion_ima_db" "imapos_db"

echo "Actualizando .env..."
for f in /home/dev_taup/proyectos/sistema_gestion_ima/.env; do
  sed -i 's/^DB_NAME=gestion_ima_db$/DB_NAME=ima_db/' "$f"
done
for f in /home/dev_taup/proyectos/imapos.2.0/.env; do
  sed -i 's/^DB_NAME=gestion_ima_db$/DB_NAME=imapos_db/' "$f"
done

  echo "Actualizando docker-compose..."
  sed -i 's/gestion_ima_db/ima_db/g' /home/dev_taup/proyectos/sistema_gestion_ima/docker-compose.yml
  sed -i 's/gestion_ima_db/imapos_db/g' /home/dev_taup/proyectos/imapos.2.0/docker-compose.yml

echo "Reiniciando apps..."
sudo -u dev_taup pm2 start gestion-ima-api gestion-ima-sync IMAPOS_api IMAPOS_sheets_sync 2>/dev/null || \
  sudo -u dev_taup pm2 restart gestion-ima-api gestion-ima-sync IMAPOS_api IMAPOS_sheets_sync

echo "Verificación:"
grep '^DB_NAME=' /home/dev_taup/proyectos/sistema_gestion_ima/.env /home/dev_taup/proyectos/imapos.2.0/.env
docker exec sgi_db mysql -uroot -p"$ROOT_PW" -N -e "SHOW DATABASES LIKE 'ima_db';"
docker exec imapos_db mysql -uroot -p"$ROOT_PW" -N -e "SHOW DATABASES LIKE 'imapos_db';"
curl -sf http://127.0.0.1:8011/api/health && echo " IMA API OK"
curl -sf http://127.0.0.1:8033/api/health && echo " IMAPOS API OK"

echo "Listo."
