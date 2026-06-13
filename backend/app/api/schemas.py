from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


Period = Literal["7d", "30d", "6m", "all"]


class TopTrack(BaseModel):
    track_id: str
    name: str
    artist_name: str
    play_count: int = Field(ge=0)


class TopArtist(BaseModel):
    artist_id: str
    name: str
    play_count: int = Field(ge=0)


class TopTag(BaseModel):
    tag: str
    listen_count: int = Field(ge=0)


class TopTrackDetail(BaseModel):
    rank: int = Field(ge=1)
    track_id: str
    name: str
    artist_name: str
    album: str | None = None
    play_count: int = Field(ge=0)
    total_ms_played: int = Field(ge=0)
    mood_label: str | None = None
    mood_confidence: float | None = Field(default=None, ge=0, le=1)
    top_tags: list[str]


class TopTracksResponse(BaseModel):
    period: Period
    limit: int = Field(ge=1, le=50)
    tracks: list[TopTrackDetail]


class MoodDistribution(BaseModel):
    happy: int = Field(ge=0)
    sad: int = Field(ge=0)
    angry: int = Field(ge=0)
    calm: int = Field(ge=0)
    energetic: int = Field(ge=0)
    melancholic: int = Field(ge=0)
    unclassified: int = Field(ge=0)


class WeatherDailyData(BaseModel):
    date: str
    day_of_week: str
    is_weekend: bool
    total_listens: int = Field(ge=0)
    mood_score: float | None = Field(default=None, ge=0, le=1)
    mood_distribution: MoodDistribution
    temp_c: float | None = None
    temp_min_c: float | None = None
    temp_max_c: float | None = None
    precipitation: float | None = None
    rain: float | None = None
    snowfall: float | None = None
    precipitation_hours: float | None = None
    weather_code: int | None = None
    weather_category: str
    temperature_bucket: str
    season: str
    had_precipitation: bool


class WeatherSummary(BaseModel):
    label: str
    total_days: int = Field(ge=0)
    total_listens: int = Field(ge=0)
    avg_listens_per_day: float = Field(ge=0)
    avg_mood_score: float | None = Field(default=None, ge=0, le=1)
    avg_temp_c: float | None = None
    total_precipitation: float = Field(ge=0)
    top_tags: list[TopTag]


class WeatherCorrelationResponse(BaseModel):
    period: Period
    weather_city: str
    daily_data: list[WeatherDailyData]
    summary_by_weather: list[WeatherSummary]
    summary_by_temperature: list[WeatherSummary]
    summary_by_season: list[WeatherSummary]


class CityOption(BaseModel):
    id: str
    name: str
    label: str
    country: str
    country_code: str
    admin1: str | None = None
    latitude: float
    longitude: float


class AppSettingsResponse(BaseModel):
    weather_city: str
    weather_latitude: float | None = None
    weather_longitude: float | None = None
    weather_refresh_status: str | None = None


class AppSettingsUpdate(BaseModel):
    weather_city: str = Field(min_length=1, max_length=120)
    weather_latitude: float | None = Field(default=None, ge=-90, le=90)
    weather_longitude: float | None = Field(default=None, ge=-180, le=180)


class OverviewResponse(BaseModel):
    period: Period
    total_listens: int = Field(ge=0)
    unique_tracks: int = Field(ge=0)
    unique_artists: int = Field(ge=0)
    top_tracks: list[TopTrack]
    top_artists: list[TopArtist]
    top_tags: list[TopTag]
    mood_breakdown: dict[str, int]
