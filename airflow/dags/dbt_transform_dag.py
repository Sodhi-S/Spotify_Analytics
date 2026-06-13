from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.sensors.external_task import ExternalTaskSensor

from _shared import PROJECT_ROOT, notify_failure

DEFAULT_ARGS = {
    "owner": "sahej",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(seconds=60),
    "on_failure_callback": notify_failure,
}

DBT_DIR = Path(PROJECT_ROOT) / "dbt"

with DAG(
    dag_id="dbt_transform_dag",
    description="Run dbt transformations, tests, and docs after quality gates pass.",
    default_args=DEFAULT_ARGS,
    schedule="*/30 * * * *",
    start_date=datetime(2026, 3, 1),
    catchup=True,
    max_active_runs=1,
    tags=["spotify_analytics", "dbt"],
) as dag:
    wait_for_data_quality = ExternalTaskSensor(
        task_id="wait_for_data_quality",
        external_dag_id="data_quality_dag",
        external_task_id="enforce_quality_gate",
        allowed_states=["success"],
        failed_states=["failed"],
        mode="reschedule",
        timeout=60 * 25,
    )

    dbt_snapshot = BashOperator(
        task_id="dbt_snapshot",
        bash_command=f"cd {DBT_DIR} && dbt snapshot",
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=(
            f"cd {DBT_DIR} && dbt run "
            "--vars '{"
            '"start_date": {% if dag_run and dag_run.conf and dag_run.conf.get("start_date") %}'
            '"{{ dag_run.conf.get("start_date") }}"{% else %}null{% endif %}, '
            '"end_date": {% if dag_run and dag_run.conf and dag_run.conf.get("end_date") %}'
            '"{{ dag_run.conf.get("end_date") }}"{% else %}null{% endif %}'
            "}'"
        ),
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"cd {DBT_DIR} && dbt test",
    )

    dbt_docs_generate = BashOperator(
        task_id="dbt_docs_generate",
        bash_command=f"cd {DBT_DIR} && dbt docs generate",
    )

    wait_for_data_quality >> dbt_snapshot >> dbt_run >> dbt_test >> dbt_docs_generate
