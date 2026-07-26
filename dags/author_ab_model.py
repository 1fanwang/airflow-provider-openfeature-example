"""Persona B (DAG author): gate a code path on a flag from inside a task.

Reads ``author.model_ab`` through the provider's ``gate`` and runs the chosen arm. No platform access
needed; the split lives in the backend, and the task logs which arm it got.
"""

from __future__ import annotations

import datetime

from airflow import DAG

try:
    from airflow.providers.standard.operators.python import PythonOperator
except ImportError:  # Airflow 2.x
    from airflow.operators.python import PythonOperator


def run_model(**context):
    from openfeature_airflow.gate import variant

    ti = context["ti"]
    dag_id = context["dag"].dag_id
    entity = f"{dag_id}:{ti.task_id}"
    arm = variant("author.model_ab", entity, "control", dag_id=dag_id, task_id=ti.task_id)
    print(f"[author_ab_model] flag resolved arm={arm!r}; running the {arm} implementation")
    return arm


with DAG(
    dag_id="author_ab_model",
    schedule=None,
    start_date=datetime.datetime(2024, 1, 1),
    catchup=False,
    tags=["openfeature", "author"],
):
    PythonOperator(task_id="run_model", python_callable=run_model)
