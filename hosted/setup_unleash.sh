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

# Second flag: the A/B experiment (author.model_ab), a 50/50 treatment/control variant split.
FLAG2=author.model_ab
echo "create flag $FLAG2"
curl -s -X POST "$BASE/api/admin/projects/$PROJ/features" -H "$ADMIN" -H 'content-type: application/json' \
  -d "{\"name\":\"$FLAG2\",\"type\":\"experiment\",\"description\":\"Assigns author DAG runs to treatment/control\"}" \
  -o /dev/null -w "  -> %{http_code}\n" || true

echo "strategy 100% + variants treatment/control 50/50 in $ENV"
curl -s -X POST "$BASE/api/admin/projects/$PROJ/features/$FLAG2/environments/$ENV/strategies" \
  -H "$ADMIN" -H 'content-type: application/json' \
  -d "{\"name\":\"flexibleRollout\",\"parameters\":{\"rollout\":\"100\",\"stickiness\":\"default\",\"groupId\":\"$FLAG2\"}}" \
  -o /dev/null -w "  -> %{http_code}\n" || true
curl -s -X PUT "$BASE/api/admin/projects/$PROJ/features/$FLAG2/environments/$ENV/variants" \
  -H "$ADMIN" -H 'content-type: application/json' \
  -d '[{"name":"treatment","weightType":"variable","weight":500,"stickiness":"default"},{"name":"control","weightType":"variable","weight":500,"stickiness":"default"}]' \
  -o /dev/null -w "  -> %{http_code}\n" || true
curl -s -X POST "$BASE/api/admin/projects/$PROJ/features/$FLAG2/environments/$ENV/on" \
  -H "$ADMIN" -o /dev/null -w "  -> %{http_code}\n" || true

echo "done"
