from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.sensors.external_task import ExternalTaskSensor

from _shared import notify_failure
from app.pipeline.music2emo_jobs import (
    fetch_music2emo_previews,
    find_unscored_music2emo_tracks,
    rebuild_music2emo_models,
    run_music2emo_inference,
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
    description="Find tracks with previews and score valence/energy using Music2Emo.",
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

    refresh_tracks_before_lookup_task = PythonOperator(
        task_id="refresh_tracks_before_lookup",
        python_callable=rebuild_music2emo_models,
    )

    find_unscored_tracks_task = PythonOperator(
        task_id="find_unscored_tracks",
        python_callable=find_unscored_music2emo_tracks,
    )

    fetch_itunes_previews_task = PythonOperator(
        task_id="fetch_itunes_previews",
        python_callable=fetch_music2emo_previews,
    )

    run_music2emo_inference_task = PythonOperator(
        task_id="run_music2emo_inference",
        python_callable=run_music2emo_inference,
    )

    refresh_tracks_after_inference_task = PythonOperator(
        task_id="refresh_tracks_after_inference",
        python_callable=rebuild_music2emo_models,
    )

    (
        wait_for_lastfm_ingest
        >> refresh_tracks_before_lookup_task
        >> find_unscored_tracks_task
        >> fetch_itunes_previews_task
        >> run_music2emo_inference_task
        >> refresh_tracks_after_inference_task
    )
