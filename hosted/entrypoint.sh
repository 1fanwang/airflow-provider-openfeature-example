#!/usr/bin/env bash
# Entrypoint for the hosted, publicly read-only demo (single container).
# Runs flagd + the scheduler + a live-activity loop, and serves the webserver on $PORT.
set -uo pipefail
export AIRFLOW_HOME="${AIRFLOW_HOME:-/opt/airflow}"

# Render hands us postgres://...; SQLAlchemy/Airflow wants postgresql+psycopg2://...
if [ -n "${AIRFLOW__DATABASE__SQL_ALCHEMY_CONN:-}" ]; then
  conn="${AIRFLOW__DATABASE__SQL_ALCHEMY_CONN}"
  conn="${conn/#postgres:\/\//postgresql+psycopg2://}"
  conn="${conn/#postgresql:\/\//postgresql+psycopg2://}"
  export AIRFLOW__DATABASE__SQL_ALCHEMY_CONN="$conn"
fi

# flagd, file-based with sub-second hot reload, on 8013.
flagd start --uri "file:${AIRFLOW_HOME}/flags/flags.json" --port 8013 &

# One-time init: schema, a maintainer admin (public visitors stay read-only via
# webserver_config.py AUTH_ROLE_PUBLIC=Viewer), and the canary pool.
airflow db migrate
airflow users create -r Admin -u "${ADMIN_USER:-admin}" -p "${ADMIN_PASSWORD:-admin}" \
  -e admin@example.com -f Admin -l User 2>/dev/null || true
airflow pools set canary_pool 128 "Canary pool for the demo" 2>/dev/null || true

# Scheduler in the background.
airflow scheduler &

# Keep the demo alive: ramp the flag and trigger the DAGs on a loop, so a visitor
# always sees fresh runs with a live canary split.
(
  sleep 45
  while true; do
    for pct in 0 20 40 60 40 20; do
      python3 - "$pct" <<'PY' || true
import json, os, sys
p = f"{os.environ.get('AIRFLOW_HOME', '/opt/airflow')}/flags/flags.json"
d = json.load(open(p))
pct = int(sys.argv[1])
d["flags"]["airflow.task.pool"]["targeting"] = {"fractional": [["canary", pct], ["default", 100 - pct]]}
json.dump(d, open(p, "w"), indent=2)
PY
      airflow dags trigger platform_pool_canary 2>/dev/null || true
      airflow dags trigger author_ab_experiment 2>/dev/null || true
      sleep 240
    done
  done
) &

# Webserver in the foreground on Render's $PORT. Anonymous access is Viewer (read-only).
exec airflow webserver --port "${PORT:-8080}" --hostname 0.0.0.0
