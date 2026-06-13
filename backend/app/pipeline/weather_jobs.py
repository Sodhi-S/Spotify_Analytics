from __future__ import annotations

from datetime import date

from app.core.alerts import send_slack_alert
from app.core.config import get_settings
from app.db import db_connection
from app.ingestion.loader import RawLoader
from app.ingestion.openmeteo import OpenMeteoClient


def fetch_daily_weather(target_date: date | None = None) -> dict[str, object]:
    settings = get_settings()
    client = OpenMeteoClient()
    try:
        weather = client.get_daily_weather(settings.openmeteo_city, target_date=target_date)
        with db_connection() as connection:
            RawLoader(connection).upsert_weather(weather)
        return weather
    except Exception as exc:
        send_slack_alert("weather", f"Weather ingestion failed: {exc}")
        raise
