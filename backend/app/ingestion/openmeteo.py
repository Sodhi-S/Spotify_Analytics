from __future__ import annotations

from datetime import date
from typing import Any

from app.ingestion.http import get_json

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
NORTH_AMERICA_COUNTRY_CODES = {
    "AG",
    "AI",
    "AW",
    "BB",
    "BL",
    "BM",
    "BQ",
    "BS",
    "BZ",
    "CA",
    "CR",
    "CU",
    "CW",
    "DM",
    "DO",
    "GD",
    "GL",
    "GP",
    "GT",
    "HN",
    "HT",
    "JM",
    "KN",
    "KY",
    "LC",
    "MF",
    "MQ",
    "MS",
    "MX",
    "NI",
    "PA",
    "PM",
    "PR",
    "SV",
    "SX",
    "TC",
    "TT",
    "US",
    "VC",
    "VG",
    "VI",
}

DAILY_WEATHER_VARIABLES = [
    "weather_code",
    "temperature_2m_mean",
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "rain_sum",
    "snowfall_sum",
    "precipitation_hours",
]


class OpenMeteoClient:
    def search_north_america_cities(self, query: str, count: int = 15) -> list[dict[str, Any]]:
        cleaned = query.strip()
        if len(cleaned) < 2:
            return []

        payload = get_json(
            GEOCODE_URL,
            {"name": cleaned, "count": 50, "language": "en", "format": "json"},
            timeout=15,
        )
        results = payload.get("results", [])
        cities: list[dict[str, Any]] = []
        for result in results:
            country_code = str(result.get("country_code") or "").upper()
            if country_code not in NORTH_AMERICA_COUNTRY_CODES:
                continue

            name = str(result.get("name") or cleaned)
            admin1 = result.get("admin1")
            country = str(result.get("country") or country_code)
            label_parts = [name]
            if admin1:
                label_parts.append(str(admin1))
            label_parts.append(country)
            latitude = float(result["latitude"])
            longitude = float(result["longitude"])
            cities.append(
                {
                    "id": f"{result.get('id', name)}-{country_code}",
                    "name": name,
                    "label": ", ".join(label_parts),
                    "country": country,
                    "country_code": country_code,
                    "admin1": admin1,
                    "latitude": latitude,
                    "longitude": longitude,
                }
            )
            if len(cities) >= count:
                break
        return cities

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

    def _location(
        self,
        city: str,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> dict[str, Any]:
        if latitude is not None and longitude is not None:
            return {"city": city, "latitude": latitude, "longitude": longitude}
        return self.geocode_city(city)

    def get_daily_weather(
        self,
        city: str,
        target_date: date | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> dict[str, Any]:
        location = self._location(city, latitude, longitude)
        payload = get_json(
            FORECAST_URL,
            {
                "latitude": location["latitude"],
                "longitude": location["longitude"],
                "daily": ",".join(DAILY_WEATHER_VARIABLES),
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
            "temp_c": _daily_value(daily, "temperature_2m_max", index),
            "temp_mean_c": _daily_value(daily, "temperature_2m_mean", index),
            "temp_min_c": _daily_value(daily, "temperature_2m_min", index),
            "precipitation": _daily_value(daily, "precipitation_sum", index),
            "rain": _daily_value(daily, "rain_sum", index),
            "snowfall": _daily_value(daily, "snowfall_sum", index),
            "precipitation_hours": _daily_value(daily, "precipitation_hours", index),
            "weather_code": _daily_value(daily, "weather_code", index),
            "source": "open_meteo_forecast",
        }

    def get_historical_daily_weather(
        self,
        city: str,
        start_date: date,
        end_date: date,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> list[dict[str, Any]]:
        if end_date < start_date:
            return []

        location = self._location(city, latitude, longitude)
        payload = get_json(
            ARCHIVE_URL,
            {
                "latitude": location["latitude"],
                "longitude": location["longitude"],
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "daily": ",".join(DAILY_WEATHER_VARIABLES),
                "timezone": "auto",
                "temperature_unit": "celsius",
                "precipitation_unit": "mm",
            },
            timeout=45,
        )
        daily = payload.get("daily", {})
        dates = daily.get("time", [])
        if not dates:
            raise ValueError("Open-Meteo historical response is missing daily.time")

        rows: list[dict[str, Any]] = []
        for index, day in enumerate(dates):
            rows.append(
                {
                    "date": date.fromisoformat(day),
                    "city": location["city"],
                    "temp_c": _daily_value(daily, "temperature_2m_max", index),
                    "temp_mean_c": _daily_value(daily, "temperature_2m_mean", index),
                    "temp_min_c": _daily_value(daily, "temperature_2m_min", index),
                    "precipitation": _daily_value(daily, "precipitation_sum", index),
                    "rain": _daily_value(daily, "rain_sum", index),
                    "snowfall": _daily_value(daily, "snowfall_sum", index),
                    "precipitation_hours": _daily_value(daily, "precipitation_hours", index),
                    "weather_code": _daily_value(daily, "weather_code", index),
                    "source": "open_meteo_archive",
                }
            )
        return rows


def _daily_value(daily: dict[str, Any], key: str, index: int) -> Any:
    values = daily.get(key, [])
    if index >= len(values):
        return None
    return values[index]
