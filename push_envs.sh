#!/bin/bash
# Push env vars to a Coolify app
# Usage: bash push_envs.sh <APP_UUID> <YOUTUBE_API_KEY> [TELEGRAM_BOT_TOKEN]

set -e

COOLIFY_URL="https://coolify.inkora.art"
COOLIFY_TOKEN="5|S0MeeJ3J5RjzeLH9Kny2VNWohwqtOZk4GtAvf4FTcfc4becd"
RESOLVE="--resolve coolify.inkora.art:443:82.25.117.199"

APP_UUID="${1:?Usage: push_envs.sh <APP_UUID> <YOUTUBE_API_KEY> [TELEGRAM_BOT_TOKEN]}"
YOUTUBE_API_KEY="${2:?Fournir la YOUTUBE_API_KEY}"
TELEGRAM_BOT_TOKEN="${3:-}"

ENV_DATA=$(cat <<ENDJSON
{
  "data": [
    {"key": "YOUTUBE_API_KEY", "value": "$YOUTUBE_API_KEY", "is_build_time": false, "is_preview": false},
    {"key": "TELEGRAM_BOT_TOKEN", "value": "$TELEGRAM_BOT_TOKEN", "is_build_time": false, "is_preview": false},
    {"key": "TELEGRAM_CHAT_ID", "value": "7445971784", "is_build_time": false, "is_preview": false},
    {"key": "PORT", "value": "3000", "is_build_time": false, "is_preview": false},
    {"key": "TZ", "value": "Europe/Paris", "is_build_time": false, "is_preview": false},
    {"key": "PYTHONIOENCODING", "value": "utf-8", "is_build_time": false, "is_preview": false}
  ]
}
ENDJSON
)

echo "=== Push env vars vers app $APP_UUID ==="
curl -sk $RESOLVE -X PATCH \
  -H "Authorization: Bearer $COOLIFY_TOKEN" \
  -H "Content-Type: application/json" \
  -d "$ENV_DATA" \
  "$COOLIFY_URL/api/v1/applications/$APP_UUID/envs/bulk"

echo ""
echo "=== Deploy app ==="
curl -sk $RESOLVE \
  -H "Authorization: Bearer $COOLIFY_TOKEN" \
  "$COOLIFY_URL/api/v1/applications/$APP_UUID/restart"

echo ""
echo "Done! App en cours de deploiement."
