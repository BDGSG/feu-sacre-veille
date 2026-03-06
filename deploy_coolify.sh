#!/bin/bash
# Deploy feu-sacre-veille to Coolify
# Usage: bash deploy_coolify.sh <YOUTUBE_API_KEY> [TELEGRAM_BOT_TOKEN]

set -e

COOLIFY_URL="https://coolify.inkora.art"
COOLIFY_TOKEN="5|S0MeeJ3J5RjzeLH9Kny2VNWohwqtOZk4GtAvf4FTcfc4becd"
SERVER_UUID="mcgwwcko00gg4k4804sw8044"
RESOLVE="--resolve coolify.inkora.art:443:82.25.117.199"

YOUTUBE_API_KEY="${1:?Usage: deploy_coolify.sh <YOUTUBE_API_KEY> [TELEGRAM_BOT_TOKEN]}"
TELEGRAM_BOT_TOKEN="${2:-}"
TELEGRAM_CHAT_ID="7445971784"

echo "=== 1. Creation du projet Coolify ==="
PROJECT=$(curl -sk $RESOLVE -X POST \
  -H "Authorization: Bearer $COOLIFY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"feu-sacre-veille","description":"Veille concurrentielle YouTube - Feu Sacre"}' \
  "$COOLIFY_URL/api/v1/projects")

PROJECT_UUID=$(echo "$PROJECT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('uuid',''))" 2>/dev/null || echo "")
echo "Project UUID: $PROJECT_UUID"

echo ""
echo "=== IMPORTANT ==="
echo "Maintenant, creez l'application manuellement dans Coolify UI:"
echo "1. Allez sur $COOLIFY_URL"
echo "2. Projet: feu-sacre-veille"
echo "3. Ajoutez une app Docker Compose"
echo "4. Collez le contenu de docker-compose.yml"
echo "5. Notez le UUID de l'app puis lancez:"
echo ""
echo "   bash push_envs.sh <APP_UUID> $YOUTUBE_API_KEY $TELEGRAM_BOT_TOKEN"
echo ""
