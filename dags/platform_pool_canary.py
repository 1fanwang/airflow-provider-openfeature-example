"""Persona A (platform): this DAG has no feature-flag code.

The cluster policy reads ``airflow.task.pool`` from flagd for each task and moves a subset onto
``canary_pool``. Ramp the flag (``./scripts/ramp.sh 30``) and the next parse moves more tasks to the
canary pool; set it to 0 for the kill switch. The DAG source never changes.
"""

from __future__ import annotations

import datetime

from airflow import DAG

try:
    from airflow.providers.standard.operators.empty import EmptyOperator
except ImportError:  # Airflow 2.x
    from airflow.operators.empty import EmptyOperator

with DAG(
    dag_id="platform_pool_canary",
    schedule=None,
    start_date=datetime.datetime(2024, 1, 1),
    catchup=False,
    tags=["openfeature", "platform"],
):
    for i in range(10):
        EmptyOperator(task_id=f"task_{i}", pool="default_pool")
