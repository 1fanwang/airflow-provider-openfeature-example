# airflow-provider-openfeature-example

A runnable Apache Airflow that comes with
[`airflow-provider-openfeature`](https://github.com/1fanwang/airflow-provider-openfeature) installed and
a [flagd](https://flagd.dev) feature-flag backend alongside it. One command boots real Airflow. A flag
then moves a subset of tasks to a canary pool, ramps it, and reverts, without editing a DAG.

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/1fanwang/airflow-provider-openfeature-example)
[![Open in Gitpod](https://gitpod.io/button/open-in-gitpod.svg)](https://gitpod.io/#https://github.com/1fanwang/airflow-provider-openfeature-example)

## See it live, no install or login

A public, always-on instance runs on Azure (Airflow 3.3.0, provider reading a real
[Flipt](https://flipt.io) backend over OFREP):

| Surface | URL | What it shows |
|---|---|---|
| Demo home | <https://ofopenfeature780983.eastus.cloudapp.azure.com/> | a landing page explaining the demo, with links into Airflow and Flipt |
| Airflow UI | <https://ofopenfeature780983.eastus.cloudapp.azure.com/dags> | tasks landing in `canary_pool`, driven by a flag |
| Flipt admin UI | <https://ofopenfeature780983.eastus.cloudapp.azure.com/flipt> | change the rollout or flip the kill switch, then watch Airflow react |

The provider itself lives at
[`airflow-provider-openfeature`](https://github.com/1fanwang/airflow-provider-openfeature)
([PyPI](https://pypi.org/project/airflow-provider-openfeature/)). Prefer to run it yourself? Keep reading.

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

### The full A/B loop: measure which arm wins

`dags/author_ab_experiment.py` goes further. It assigns 200 shards to treatment or control by the flag,
runs the matching aggregation, records each real elapsed time with the provider's `track_outcome`, then
reads the result with its standard-library `analysis` (SRM and lift). No experiment-platform account needed.

```bash
docker compose exec airflow-scheduler airflow dags test author_ab_experiment 2024-01-02
```

Real output:

```
[experiment] counts={'treatment': 95, 'control': 105}  means_ms={treatment: 0.046, control: 0.260}
[experiment] SRM ok=True (p=0.480) -- the split matches the flag
[experiment] lift(treatment vs control) = -82.1%  (negative means treatment is faster)
```

SRM confirms the split landed where the flag said, so the lift is trustworthy: treatment is 82% faster.
`track_outcome` sends the same events to Statsig, GrowthBook, or your warehouse the moment you point
`config/airflow_local_settings.py` at one. The demo has no sink, so the verdict is read from the run.

> On the **hosted** demo (Airflow 3.x, LocalExecutor) the canary runs live, but this A/B DAG's Python
> tasks are not auto-scheduled: Airflow 3.x's Task SDK supervisor is multi-threaded and forking a task
> worker from it deadlocks the child at startup, independent of this provider. Run the A/B on this local
> demo (Airflow 2.11, no fork issue) or with `airflow tasks test`, as shown above.

## Point it at your own backend

The demo uses flagd because it runs locally with no account. The provider reads any OpenFeature backend,
so swap flagd for LaunchDarkly, GrowthBook, Unleash, Statsig, or an in-house engine by changing the one
line in `config/airflow_local_settings.py`. The DAGs and the policy stay the same. The full backend list
and how to add your own are in the provider's
[Extending guide](https://github.com/1fanwang/airflow-provider-openfeature/blob/main/docs/extending.md).

## Run it in your own Airflow

This repo is a prebuilt demo. To wire the provider into an Airflow you already run (install, enable the
policy, register your backend), follow the provider's
[getting-started](https://github.com/1fanwang/airflow-provider-openfeature/blob/main/docs/getting-started.md),
and see [Architecture](https://github.com/1fanwang/airflow-provider-openfeature/blob/main/docs/architecture.md)
and [Use cases](https://github.com/1fanwang/airflow-provider-openfeature/blob/main/docs/use-cases.md) for
the concepts and the measurement loop.

## Clean up

```bash
docker compose down -v          # or: make down
```

## Tested

The stack here is exercised end to end in CI (`.github/workflows/e2e.yml`): it boots Airflow and flagd,
ramps the flag to 100%, asserts every task moved to `canary_pool`, flips the kill switch, and asserts
they all revert. If the demo breaks, CI goes red.
