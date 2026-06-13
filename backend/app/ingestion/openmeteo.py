from __future__ import annotations

from datetime import date
from typing import Any

from app.ingestion.http import get_json

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


class OpenMeteoClient:
    def geocode_city(self, city: str) -> dict[str, Any]:
        payload = get_json(GEOCODE_URL, {"name": city, "count": 1, "language": "en"})
        results = payload.get("results", [])
        if not results:
            raise ValueError(f"No Open-Meteo geocode result for city={city!r}")
        result = results[0]
        return {
            "city": result.get("name") or city,
            "latitude": result["latitude"],
            "longitude": result["longitude"],
        }

    def get_daily_weather(self, city: str, target_date: date | None = None) -> dict[str, Any]:
        location = self.geocode_city(city)
        payload = get_json(
            FORECAST_URL,
            {
                "latitude": location["latitude"],
                "longitude": location["longitude"],
                "daily": ",".join(
                    ["temperature_2m_max", "precipitation_sum", "weather_code"]
                ),
                "timezone": "auto",
                "past_days": 7,
                "forecast_days": 1,
            },
        )
        daily = payload.get("daily", {})
        dates = daily.get("time", [])
        if not dates:
            raise ValueError("Open-Meteo response is missing daily.time")

        requested = target_date.isoformat() if target_date else dates[-1]
        index = dates.index(requested) if requested in dates else len(dates) - 1
        return {
            "date": date.fromisoformat(dates[index]),
            "city": location["city"],
            "temp_c": daily["temperature_2m_max"][index],
            "precipitation": daily["precipitation_sum"][index],
            "weather_code": daily["weather_code"][index],
        }
