from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.api.schemas import AppSettingsResponse, AppSettingsUpdate
from app.core.config import get_settings

WEATHER_CITY_KEY = "weather_city"
WEATHER_LATITUDE_KEY = "weather_latitude"
WEATHER_LONGITUDE_KEY = "weather_longitude"


def clean_weather_city(city: str) -> str:
    cleaned = " ".join(city.strip().split())
    if not cleaned:
        raise ValueError("Weather city is required")
    if len(cleaned) > 120:
        raise ValueError("Weather city must be 120 characters or fewer")
    return cleaned


@dataclass(frozen=True)
class WeatherLocation:
    city: str
    latitude: float | None = None
    longitude: float | None = None


def _settings_map(connection: Connection) -> dict[str, str]:
    rows = connection.execute(
        text(
            """
            select key, value
            from raw.user_settings
            """
        )
    )
    return {row._mapping["key"]: row._mapping["value"] for row in rows}


def _float_setting(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def get_weather_location(connection: Connection) -> WeatherLocation:
    values = _settings_map(connection)
    city = clean_weather_city(values.get(WEATHER_CITY_KEY) or get_settings().openmeteo_city or "Toronto")
    return WeatherLocation(
        city=city,
        latitude=_float_setting(values.get(WEATHER_LATITUDE_KEY)),
        longitude=_float_setting(values.get(WEATHER_LONGITUDE_KEY)),
    )


def get_weather_city(connection: Connection) -> str:
    return get_weather_location(connection).city


class SettingsService:
    def __init__(self, connection: Connection):
        self.connection = connection

    def get_settings(self) -> AppSettingsResponse:
        location = get_weather_location(self.connection)
        return AppSettingsResponse(
            weather_city=location.city,
            weather_latitude=location.latitude,
            weather_longitude=location.longitude,
        )

    def update_settings(self, settings_update: AppSettingsUpdate) -> AppSettingsResponse:
        weather_city = clean_weather_city(settings_update.weather_city)
        rows = [
            {"key": WEATHER_CITY_KEY, "value": weather_city},
            {
                "key": WEATHER_LATITUDE_KEY,
                "value": (
                    str(settings_update.weather_latitude)
                    if settings_update.weather_latitude is not None
                    else ""
                ),
            },
            {
                "key": WEATHER_LONGITUDE_KEY,
                "value": (
                    str(settings_update.weather_longitude)
                    if settings_update.weather_longitude is not None
                    else ""
                ),
            },
        ]
        self.connection.execute(
            text(
                """
                insert into raw.user_settings (key, value, updated_at)
                values (:key, :value, current_timestamp)
                on conflict (key) do update set
                    value = excluded.value,
                    updated_at = current_timestamp
                """
            ),
            rows,
        )
        return AppSettingsResponse(
            weather_city=weather_city,
            weather_latitude=settings_update.weather_latitude,
            weather_longitude=settings_update.weather_longitude,
        )
