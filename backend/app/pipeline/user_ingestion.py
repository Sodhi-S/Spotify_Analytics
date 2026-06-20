from __future__ import annotations

import shutil
import subprocess
from typing import Any

from app.core.config import ROOT_DIR, get_settings
from app.db import db_connection
from app.pipeline.lastfm_jobs import run_lastfm_ingestion
from app.pipeline.weather_jobs import fetch_historical_weather
from app.services.auth import update_ingestion_job


def run_user_initial_import(
    user_id: str,
    lastfm_username: str,
    job_id: str,
) -> None:
    with db_connection() as connection:
        update_ingestion_job(connection, job_id, "running")

    try:
        result: dict[str, Any] = {
            "lastfm": run_lastfm_ingestion(
                user_id=user_id,
                lastfm_username=lastfm_username,
            ),
            "weather": fetch_historical_weather(user_id=user_id),
            "dbt": rebuild_lastfm_models(),
        }
    except Exception as exc:  # noqa: BLE001 - stored so the frontend can show status.
        with db_connection() as connection:
            update_ingestion_job(connection, job_id, "failed", error_message=str(exc))
        raise

    with db_connection() as connection:
        update_ingestion_job(connection, job_id, "succeeded", result=result)


def rebuild_lastfm_models() -> list[dict[str, object]]:
    commands = [
        [
            _dbt_executable(),
            "run",
            "--profiles-dir",
            ".",
            "--select",
            "stg_recent_tracks",
            "stg_track_tags",
            "stg_artists",
            "stg_artist_tags",
            "int_listens_enriched",
            "int_artists_snapshot",
            "dim_tracks",
        ],
        [
            _dbt_executable(),
            "snapshot",
            "--profiles-dir",
            ".",
            "--select",
            "artists_snapshot",
        ],
        [
            _dbt_executable(),
            "run",
            "--profiles-dir",
            ".",
            "--select",
            "dim_artists",
            "fact_listens",
            "mart_listening_summary",
            "mart_tag_listen_counts",
        ],
    ]
    results: list[dict[str, object]] = []
    for command in commands:
        result = subprocess.run(
            command,
            cwd=ROOT_DIR / "dbt",
            check=True,
            capture_output=True,
            text=True,
        )
        results.append(
            {
                "command": " ".join(command),
                "returncode": result.returncode,
            }
        )
    return results


def _dbt_executable() -> str:
    configured = get_settings().dbt_executable
    if shutil.which(configured):
        return configured

    local_conda_dbt = "/opt/anaconda3/envs/ve/bin/dbt"
    if shutil.which(local_conda_dbt):
        return local_conda_dbt

    return configured
