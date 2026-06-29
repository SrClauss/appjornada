#!/usr/bin/env bash
set -euo pipefail

SERVER="root@2.24.121.189"
REMOTE_DIR="/src/app_jornada"
LOCAL_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Garantindo que $REMOTE_DIR existe no servidor ..."
ssh "$SERVER" "mkdir -p $REMOTE_DIR"

echo "==> Sincronizando $LOCAL_DIR → $SERVER:$REMOTE_DIR ..."
rsync -avz --delete \
  --exclude='.git' \
  --exclude='node_modules' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.pytest_cache' \
  --exclude='.mypy_cache' \
  --exclude='painel-controle/dist' \
  --exclude='painel-controle/.vite' \
  --exclude='backend/.venv' \
  --exclude='backend/venv' \
  --exclude='osrm_data' \
  --exclude='app_motorista/build' \
  --exclude='app_motorista/.dart_tool' \
  --exclude='app_motorista/.flutter-plugins*' \
  "$LOCAL_DIR/" \
  "$SERVER:$REMOTE_DIR/"

echo "==> Executando docker compose up --build no servidor ..."
ssh "$SERVER" bash <<EOF
  set -euo pipefail
  cd "$REMOTE_DIR"
  docker compose up -d --build
  echo "==> Containers em execução:"
  docker compose ps
EOF

echo ""
echo "==> Deploy concluído! Acesse http://2.24.121.189:3000"
