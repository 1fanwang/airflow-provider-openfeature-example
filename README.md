# airflow-provider-openfeature-example

A runnable Apache Airflow that comes with
[`airflow-provider-openfeature`](https://github.com/1fanwang/airflow-provider-openfeature) installed and
a [flagd](https://flagd.dev) feature-flag backend alongside it. One command boots real Airflow. A flag
then moves a subset of tasks to a canary pool, ramps it, and reverts, without editing a DAG.

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/1fanwang/airflow-provider-openfeature-example)
[![Open in Gitpod](https://gitpod.io/button/open-in-gitpod.svg)](https://gitpod.io/#https://github.com/1fanwang/airflow-provider-openfeature-example)

## Run it

You need Docker. Nothing else.

```bash
git clone https://github.com/1fanwang/airflow-provider-openfeature-example.git
cd airflow-provider-openfeature-example
docker compose up -d --build          # or: make up
```

Airflow UI: http://localhost:8080 (admin / admin). flagd listens on localhost:8013.

No local Docker? Click **Open in GitHub Codespaces** above and it runs the same stack in your browser.

## What's wired

- Airflow 2.11 (LocalExecutor), Postgres, and flagd, in one `docker-compose.yml`.
- The provider is pip-installed (`requirements.txt`), and its placement policy is turned on with
  `AIRFLOW__OPENFEATURE__ENABLE_POLICY=True`.
- `config/airflow_local_settings.py` points OpenFeature at flagd. That is the only platform wiring.
- `flags/flags.json` holds the flags. flagd hot-reloads it on save, so a ramp takes effect on the next
  DAG parse with no restart.

## Persona 1, platform: ramp a pool move with a flag

`dags/platform_pool_canary.py` has 10 tasks, all asking for `default_pool`, and **no flag code**. The
cluster policy reads `airflow.task.pool` for each task and moves a subset to `canary_pool`.

Ramp it:

```bash
./scripts/ramp.sh 100          # or: make ramp PCT=100
```

Here is the real result as the flag changes, parsing the DAG through the live policy at each step:

| flag setting | where the 10 tasks run |
|---|---|
| canary 0% | `default_pool`: 10 |
| canary 100% | `canary_pool`: 10 |
| canary 30% | `canary_pool`: 4 (task_1, task_3, task_5, task_9), `default_pool`: 6 |
| kill switch (`ramp.sh 0`) | `default_pool`: 10 |

The subset is deterministic and sticky: a task that is canary at 30% stays canary at 50%. Exact counts
follow the hash, so a 30% ramp lands a fixed subset near that fraction. The kill switch is one flag
change, no redeploy.

Where to see it: the DAG source never changes, but each task's **Pool** in the Airflow UI (Grid, then a
task, then Instance Details) reflects what the policy set. The table above is that same value read
straight from a parse.

## Persona 2, DAG author: gate a code path inside a task

`dags/author_ab_model.py` calls the provider's `gate` to pick an arm from `author.model_ab` and runs it.
No platform access needed; the split lives in the backend.

```bash
docker compose exec airflow-scheduler airflow tasks test author_ab_model run_model 2024-01-02
# [author_ab_model] flag resolved arm='treatment'; running the treatment implementation
```

## Point it at your own backend

The demo uses flagd because it runs locally with no account. The provider reads any OpenFeature backend,
so swap flagd for LaunchDarkly, GrowthBook, Unleash, Statsig, or an in-house engine by changing the one
line in `config/airflow_local_settings.py`. The DAGs and the policy stay the same.

## Clean up

```bash
docker compose down -v          # or: make down
```

## Tested

The stack here is exercised end to end in CI (`.github/workflows/e2e.yml`): it boots Airflow and flagd,
ramps the flag to 100%, asserts every task moved to `canary_pool`, flips the kill switch, and asserts
they all revert. If the demo breaks, CI goes red.
