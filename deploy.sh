#!/usr/bin/env bash
set -euo pipefail

LOCAL_DIR="$(cd "$(dirname "$0")" && pwd)"

BUILD_APK=false
COMMIT_MSG=""

# Processa os argumentos com getopts
while getopts "am:" opt; do
  case $opt in
    a)
      BUILD_APK=true
      ;;
    m)
      COMMIT_MSG="$OPTARG"
      ;;
    \?)
      echo "Opção inválida. Uso: $0 [-a] [-m 'mensagem de commit'] [mensagem de commit legado]"
      exit 1
      ;;
  esac
done

shift $((OPTIND-1))

# Mantém compatibilidade com o formato anterior (argumento posicional simples para mensagem)
if [ -z "$COMMIT_MSG" ] && [ $# -gt 0 ] && [ -n "$1" ]; then
  COMMIT_MSG="$1"
fi

# Se a flag -a foi passada, compila o APK antes do deploy
if [ "$BUILD_APK" = true ]; then
  echo "==> Iniciando compilação do APK de Produção (app_motorista)..."
  cd "$LOCAL_DIR/app_motorista"
  VERSION=$(grep '^version:' pubspec.yaml | awk '{print $2}' | cut -d'+' -f1 || echo "1.0.4")
  flutter clean
  flutter build apk --release
  mkdir -p "$LOCAL_DIR/nginx/html"
  cp build/app/outputs/flutter-apk/app-release.apk "$LOCAL_DIR/nginx/html/app-release.apk"
  cp build/app/outputs/flutter-apk/app-release.apk "$LOCAL_DIR/nginx/html/app-jornada-v${VERSION}.apk"
  cp build/app/outputs/flutter-apk/app-release.apk "$LOCAL_DIR/app-release.apk"
  cp build/app/outputs/flutter-apk/app-release.apk "$LOCAL_DIR/app-jornada-v${VERSION}.apk"
  cp build/app/outputs/flutter-apk/app-release.apk "$LOCAL_DIR/painel-controle/public/app-release.apk"
  cp build/app/outputs/flutter-apk/app-release.apk "$LOCAL_DIR/painel-controle/public/app-jornada-v${VERSION}.apk"
  cd "$LOCAL_DIR"
  echo "==> APK v${VERSION} compilado e copiado para app-jornada-v${VERSION}.apk e app-release.apk com sucesso!"
fi

# Se um comentário de commit for fornecido
if [ -n "$COMMIT_MSG" ]; then
  echo "==> Atualizando repositório local e enviando para o GitHub..."
  cd "$LOCAL_DIR"
  git add .
  git commit -m "$COMMIT_MSG" || echo "==> Sem novas alterações para commit."
  git push origin master || echo "==> Falha no git push, mas prosseguindo com o deploy..."
else
  echo "==> Nenhum comentário de commit fornecido. Pulando atualização do GitHub."
fi

SERVER="root@2.24.121.189"
REMOTE_DIR="/src/app_jornada"

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
  docker compose restart nginx
  echo "==> Containers em execução:"
  docker compose ps
EOF

echo ""
echo "==> Deploy concluído! Acesse http://2.24.121.189:3000"
