from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

from _shared import notify_failure
from app.pipeline.lastfm_jobs import (
    fetch_artist_info,
    fetch_artist_tags,
    fetch_recent_tracks,
    fetch_track_tags,
    fetch_user_charts,
)

DEFAULT_ARGS = {
    "owner": "sahej",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(seconds=60),
    "on_failure_callback": notify_failure,
}

with DAG(
    dag_id="lastfm_ingest_dag",
    description="Ingest recent Last.fm scrobbles and related track/artist metadata.",
    default_args=DEFAULT_ARGS,
    schedule="*/30 * * * *",
    start_date=datetime(2026, 3, 1),
    catchup=True,
    max_active_runs=1,
    tags=["spotify_analytics", "ingestion"],
) as dag:
    fetch_recent_tracks_task = PythonOperator(
        task_id="fetch_recent_tracks",
        python_callable=fetch_recent_tracks,
    )

    fetch_track_tags_task = PythonOperator(
        task_id="fetch_track_tags",
        python_callable=fetch_track_tags,
    )

    fetch_artist_info_task = PythonOperator(
        task_id="fetch_artist_info",
        python_callable=fetch_artist_info,
    )

    fetch_artist_tags_task = PythonOperator(
        task_id="fetch_artist_tags",
        python_callable=fetch_artist_tags,
    )

    fetch_user_charts_task = PythonOperator(
        task_id="fetch_user_charts",
        python_callable=fetch_user_charts,
    )

    (
        fetch_recent_tracks_task
        >> fetch_track_tags_task
        >> fetch_artist_info_task
        >> fetch_artist_tags_task
        >> fetch_user_charts_task
    )
