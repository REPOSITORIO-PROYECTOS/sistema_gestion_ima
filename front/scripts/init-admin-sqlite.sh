#!/usr/bin/env bash
set -euo pipefail

DB_PATH="${NEXT_ADMIN_SQLITE_PATH:-$(pwd)/admin.sqlite}"

if ! command -v sqlite3 >/dev/null 2>&1; then
  echo "sqlite3 no está instalado. Instálalo y vuelve a ejecutar." >&2
  exit 1
fi

mkdir -p "$(dirname "$DB_PATH")"

sqlite3 "$DB_PATH" <<'SQL'
CREATE TABLE IF NOT EXISTS admins (
  username TEXT PRIMARY KEY,
  password TEXT NOT NULL
);
SQL

sqlite3 "$DB_PATH" "INSERT OR REPLACE INTO admins (username, password) VALUES ('Martin', 'SistemaIMAA12345');"

chmod 600 "$DB_PATH"
echo "✅ Base creada en: $DB_PATH"

