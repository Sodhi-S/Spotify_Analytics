from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.sensors.external_task import ExternalTaskSensor

from _shared import notify_failure
from app.pipeline.mood_jobs import (
    fetch_itunes_previews,
    find_unclassified_tracks,
    run_librosa_inference,
    write_mood_labels,
)

DEFAULT_ARGS = {
    "owner": "sahej",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(seconds=60),
    "on_failure_callback": notify_failure,
}

with DAG(
    dag_id="mood_classification_dag",
    description="Find tracks with previews and classify mood using the Librosa model.",
    default_args=DEFAULT_ARGS,
    schedule="*/30 * * * *",
    start_date=datetime(2026, 3, 1),
    catchup=True,
    max_active_runs=1,
    tags=["spotify_analytics", "mood"],
) as dag:
    wait_for_lastfm_ingest = ExternalTaskSensor(
        task_id="wait_for_lastfm_ingest",
        external_dag_id="lastfm_ingest_dag",
        external_task_id=None,
        allowed_states=["success"],
        failed_states=["failed"],
        mode="reschedule",
        timeout=60 * 25,
    )

    find_unclassified_tracks_task = PythonOperator(
        task_id="find_unclassified_tracks",
        python_callable=find_unclassified_tracks,
    )

    fetch_itunes_previews_task = PythonOperator(
        task_id="fetch_itunes_previews",
        python_callable=fetch_itunes_previews,
    )

    run_librosa_inference_task = PythonOperator(
        task_id="run_librosa_inference",
        python_callable=run_librosa_inference,
    )

    write_mood_labels_task = PythonOperator(
        task_id="write_mood_labels",
        python_callable=write_mood_labels,
    )

    (
        wait_for_lastfm_ingest
        >> find_unclassified_tracks_task
        >> fetch_itunes_previews_task
        >> run_librosa_inference_task
        >> write_mood_labels_task
    )
