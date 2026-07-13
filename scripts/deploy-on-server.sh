#!/usr/bin/env bash
# Deploy manual en el servidor cuando GitHub Actions no puede conectar por SSH.
# Uso: ./scripts/deploy-on-server.sh [backend|frontend|all]
set -euo pipefail

TARGET="${1:-all}"
PROJECT_PATH="${PROJECT_PATH:-/home/dev_taup/proyectos/sistema_gestion_ima}"

export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
# shellcheck disable=SC1091
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"

PM2_BIN="$HOME/.nvm/versions/node/$(nvm version)/bin/pm2"

cd "$PROJECT_PATH"
echo "📥 Actualizando código..."
git fetch --all
git reset --hard origin/main

deploy_backend() {
  echo "🚀 Backend..."
  cd "$PROJECT_PATH/back"
  source venv/bin/activate
  pip install -r requirements.txt
  deactivate
  "$PM2_BIN" reload "$PROJECT_PATH/ecosystem.config.js" --only gestion-ima-api
  "$PM2_BIN" reload "$PROJECT_PATH/ecosystem.config.js" --only gestion-ima-sync
  echo "✅ Backend listo"
}

deploy_frontend() {
  echo "🚀 Frontend..."
  cd "$PROJECT_PATH/front"
  rm -rf .next/
  npm ci
  npm run build
  "$PM2_BIN" reload "$PROJECT_PATH/ecosystem.config.js" --only gestion-ima-front
  echo "✅ Frontend listo"
}

case "$TARGET" in
  backend) deploy_backend ;;
  frontend) deploy_frontend ;;
  all)
    deploy_backend
    deploy_frontend
    ;;
  *)
    echo "Uso: $0 [backend|frontend|all]"
    exit 1
    ;;
esac
