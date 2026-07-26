#!/usr/bin/env bash
# Ramp the platform pool canary. Run from the repo root:
#   ./scripts/ramp.sh <canary-percent 0-100>
# flagd hot-reloads flags/flags.json on save, so the next DAG parse picks up the new split.
set -euo pipefail
PCT="${1:?usage: ./scripts/ramp.sh <canary-percent 0-100>}"
python3 - "$PCT" <<'PY'
import json, sys

pct = int(sys.argv[1])
assert 0 <= pct <= 100, "percent must be 0-100"
path = "flags/flags.json"
data = json.load(open(path))
data["flags"]["airflow.task.pool"]["targeting"] = {"fractional": [["canary", pct], ["default", 100 - pct]]}
json.dump(data, open(path, "w"), indent=2)
open(path, "a").write("\n")
print(f"airflow.task.pool -> canary {pct}% / default {100 - pct}%. flagd will hot-reload.")
PY
