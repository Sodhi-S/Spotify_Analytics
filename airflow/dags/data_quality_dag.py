from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.sensors.external_task import ExternalTaskSensor

from _shared import notify_failure
from app.quality.sql_checks import (
    run_dim_tracks_mood_suite,
    run_quality_gate,
    run_raw_recent_tracks_suite,
    run_raw_weather_suite,
)

DEFAULT_ARGS = {
    "owner": "sahej",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(seconds=60),
    "on_failure_callback": notify_failure,
}

with DAG(
    dag_id="data_quality_dag",
    description="Run quality gates before dbt transformations.",
    default_args=DEFAULT_ARGS,
    schedule="*/30 * * * *",
    start_date=datetime(2026, 3, 1),
    catchup=True,
    max_active_runs=1,
    tags=["spotify_analytics", "quality"],
) as dag:
    wait_for_mood_classification = ExternalTaskSensor(
        task_id="wait_for_mood_classification",
        external_dag_id="mood_classification_dag",
        external_task_id=None,
        allowed_states=["success"],
        failed_states=["failed"],
        mode="reschedule",
        timeout=60 * 25,
    )

    run_ge_recent_tracks = PythonOperator(
        task_id="run_ge_recent_tracks",
        python_callable=run_raw_recent_tracks_suite,
    )

    run_ge_mood = PythonOperator(
        task_id="run_ge_mood",
        python_callable=run_dim_tracks_mood_suite,
    )

    run_ge_weather = PythonOperator(
        task_id="run_ge_weather",
        python_callable=run_raw_weather_suite,
    )

    enforce_gate = PythonOperator(
        task_id="enforce_quality_gate",
        python_callable=run_quality_gate,
    )

    wait_for_mood_classification >> run_ge_recent_tracks >> run_ge_mood >> run_ge_weather >> enforce_gate
