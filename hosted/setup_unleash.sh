#!/usr/bin/env sh
# Seed the real Unleash backend for the demo: create the airflow.task.pool flag as a percentage
# rollout so a subset of Airflow tasks land on canary_pool. Idempotent. Runs inside the compose
# network (curl image) against Unleash's admin API.
set -eu
BASE="${UNLEASH_BASE:-http://unleash:4242/unleash}"
ADMIN="Authorization: *:*.unleash-insecure-admin-api-token"
FLAG=airflow.task.pool
PROJ=default
ENV=development
ROLLOUT="${INIT_ROLLOUT:-30}"

echo "waiting for unleash at $BASE ..."
i=0
while [ "$i" -lt 90 ]; do
  if curl -sf "$BASE/health" >/dev/null 2>&1; then break; fi
  i=$((i + 1)); sleep 2
done

echo "create flag $FLAG"
curl -s -X POST "$BASE/api/admin/projects/$PROJ/features" -H "$ADMIN" -H 'content-type: application/json' \
  -d "{\"name\":\"$FLAG\",\"type\":\"release\",\"description\":\"Moves a % of Airflow tasks to canary_pool\"}" \
  -o /dev/null -w "  -> %{http_code}\n" || true

echo "flexibleRollout ${ROLLOUT}% in $ENV"
curl -s -X POST "$BASE/api/admin/projects/$PROJ/features/$FLAG/environments/$ENV/strategies" \
  -H "$ADMIN" -H 'content-type: application/json' \
  -d "{\"name\":\"flexibleRollout\",\"parameters\":{\"rollout\":\"$ROLLOUT\",\"stickiness\":\"default\",\"groupId\":\"$FLAG\"}}" \
  -o /dev/null -w "  -> %{http_code}\n" || true

echo "enable $FLAG in $ENV"
curl -s -X POST "$BASE/api/admin/projects/$PROJ/features/$FLAG/environments/$ENV/on" \
  -H "$ADMIN" -o /dev/null -w "  -> %{http_code}\n" || true

echo "done"
