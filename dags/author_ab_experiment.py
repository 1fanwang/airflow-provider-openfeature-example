"""Persona B, the full A/B loop: assign, run, measure, decide. No experiment-platform account needed.

Each shard is assigned to ``treatment`` or ``control`` by the ``author.model_ab`` flag, runs the matching
aggregation, and records its real elapsed time with the provider's ``track_outcome``. The final task reads
the result with the provider's standard-library ``analysis``: a sample-ratio-mismatch check (did the split
land where the flag said?) and the lift (did treatment actually win?).

``track_outcome`` also sends the same event to Statsig, GrowthBook, or your warehouse the moment you point
``airflow_local_settings`` at one; here there is no sink, so the decision is read locally from the run.
"""

from __future__ import annotations

import datetime
import time

from airflow import DAG

try:
    from airflow.providers.standard.operators.python import PythonOperator
except ImportError:  # Airflow 2.x
    from airflow.operators.python import PythonOperator

N_SHARDS = 200
DATA = list(range(20_000))


def _rollup_control(data):
    total = 0
    for x in data:  # the old path: a manual accumulate
        total += x
    return total


def _rollup_treatment(data):
    return sum(data)  # the rewrite under test


def run_experiment(**context):
    from openfeature_airflow.gate import variant
    from openfeature_airflow.measure import track_outcome

    results = []
    for shard in range(N_SHARDS):
        entity = f"author_ab_experiment:{shard}"
        arm = variant("author.model_ab", entity, "control", shard=shard)
        impl = _rollup_treatment if arm == "treatment" else _rollup_control
        start = time.perf_counter()
        impl(DATA)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        track_outcome("rollup_ms", entity, value=elapsed_ms, arm=arm)
        results.append((arm, elapsed_ms))
    return results


def read_result(**context):
    from collections import defaultdict

    from openfeature_airflow.analysis import lift, srm_check

    results = context["ti"].xcom_pull(task_ids="run_experiment")
    counts: dict[str, int] = defaultdict(int)
    totals: dict[str, float] = defaultdict(float)
    for arm, ms in results:
        counts[arm] += 1
        totals[arm] += ms
    means = {a: totals[a] / counts[a] for a in counts}

    srm = srm_check(dict(counts), {"treatment": 50, "control": 50})
    change = lift(means.get("control", 0.0), means.get("treatment", 0.0))

    print(f"[experiment] counts={dict(counts)}  means_ms={{{', '.join(f'{a}: {m:.3f}' for a, m in means.items())}}}")
    print(f"[experiment] SRM ok={srm.ok} (p={srm.p_value:.3f}) -- the split matches the flag")
    print(f"[experiment] lift(treatment vs control) = {change:.1%}  (negative means treatment is faster)")


with DAG(
    dag_id="author_ab_experiment",
    schedule=None,
    start_date=datetime.datetime(2024, 1, 1),
    catchup=False,
    tags=["openfeature", "author", "experiment"],
):
    PythonOperator(task_id="run_experiment", python_callable=run_experiment) >> PythonOperator(
        task_id="read_result", python_callable=read_result
    )
