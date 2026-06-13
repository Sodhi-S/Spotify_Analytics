from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

from _shared import notify_failure
from app.pipeline.weather_jobs import fetch_daily_weather

DEFAULT_ARGS = {
    "owner": "sahej",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(seconds=60),
    "on_failure_callback": notify_failure,
}

with DAG(
    dag_id="weather_ingest_dag",
    description="Ingest daily Open-Meteo weather data.",
    default_args=DEFAULT_ARGS,
    schedule="0 2 * * *",
    start_date=datetime(2026, 3, 1),
    catchup=True,
    max_active_runs=1,
    tags=["spotify_analytics", "ingestion"],
) as dag:
    fetch_daily_weather_task = PythonOperator(
        task_id="fetch_daily_weather",
        python_callable=fetch_daily_weather,
    )
