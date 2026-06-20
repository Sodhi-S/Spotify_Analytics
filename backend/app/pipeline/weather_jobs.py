from __future__ import annotations

import shutil
import subprocess
from datetime import date

from sqlalchemy import text

from app.core.alerts import send_slack_alert
from app.core.config import ROOT_DIR, get_settings
from app.db import db_connection
from app.ingestion.loader import RawLoader
from app.ingestion.openmeteo import OpenMeteoClient
from app.services.settings import WeatherLocation, get_weather_location


def fetch_daily_weather(
    target_date: date | None = None,
    user_id: str | None = None,
) -> dict[str, object]:
    client = OpenMeteoClient()
    try:
        with db_connection() as connection:
            location = get_weather_location(connection, user_id=user_id)
            weather = client.get_daily_weather(
                location.city,
                target_date=target_date,
                latitude=location.latitude,
                longitude=location.longitude,
            )
            RawLoader(connection).upsert_weather(weather)
        return weather
    except Exception as exc:
        send_slack_alert("weather", f"Weather ingestion failed: {exc}")
        raise


def fetch_historical_weather(
    start_date: date | None = None,
    end_date: date | None = None,
    location: WeatherLocation | None = None,
    user_id: str | None = None,
) -> dict[str, object]:
    client = OpenMeteoClient()
    try:
        with db_connection() as connection:
            weather_location = location or get_weather_location(connection, user_id=user_id)
            if start_date is None or end_date is None:
                user_filter = "where user_id = :user_id" if user_id is not None else ""
                row = connection.execute(
                    text(
                        f"""
                        select
                            min(cast(played_at as date)) as min_date,
                            max(cast(played_at as date)) as max_date
                        from raw.recent_tracks
                        {user_filter}
                        """
                    ),
                    {"user_id": user_id} if user_id is not None else {},
                ).first()
                if row is None or row._mapping["min_date"] is None:
                    return {"inserted": 0, "reason": "no listening history found"}
                start_date = start_date or row._mapping["min_date"]
                end_date = end_date or row._mapping["max_date"]

            weather_rows = client.get_historical_daily_weather(
                weather_location.city,
                start_date=start_date,
                end_date=end_date,
                latitude=weather_location.latitude,
                longitude=weather_location.longitude,
            )
            loader = RawLoader(connection)
            for weather in weather_rows:
                loader.upsert_weather(weather)

        return {
            "city": weather_location.city,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "inserted": len(weather_rows),
        }
    except Exception as exc:
        send_slack_alert("weather", f"Historical weather ingestion failed: {exc}")
        raise


def process_weather_city(
    location: WeatherLocation,
    user_id: str | None = None,
) -> dict[str, object]:
    ingestion_result = fetch_historical_weather(location=location, user_id=user_id)
    dbt_result = rebuild_weather_models()
    return {"ingestion": ingestion_result, "dbt": dbt_result}


def rebuild_weather_models() -> dict[str, object]:
    dbt_executable = _dbt_executable()
    command = [
        dbt_executable,
        "run",
        "--profiles-dir",
        ".",
        "--select",
        "stg_weather",
        "int_weather_enriched",
        "dim_weather",
        "mart_listening_summary",
        "mart_tag_listen_counts",
    ]
    result = subprocess.run(
        command,
        cwd=ROOT_DIR / "dbt",
        check=True,
        capture_output=True,
        text=True,
    )
    return {
        "command": " ".join(command),
        "returncode": result.returncode,
    }


def _dbt_executable() -> str:
    configured = get_settings().dbt_executable
    if shutil.which(configured):
        return configured

    local_conda_dbt = "/opt/anaconda3/envs/ve/bin/dbt"
    if shutil.which(local_conda_dbt):
        return local_conda_dbt

    return configured
