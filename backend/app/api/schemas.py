from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


Period = Literal["7d", "30d", "6m", "all"]


class TopTrack(BaseModel):
    track_id: str
    name: str
    artist_name: str
    play_count: int = Field(ge=0)
    album_image_url: str | None = None


class TopArtist(BaseModel):
    artist_id: str
    name: str
    play_count: int = Field(ge=0)
    image_url: str | None = None


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
    album_image_url: str | None = None


class TopTracksResponse(BaseModel):
    period: Period
    limit: int = Field(ge=1, le=50)
    tracks: list[TopTrackDetail]


class ArtistMoodFingerprint(BaseModel):
    rank: int = Field(ge=1)
    artist_id: str
    name: str
    image_url: str | None = None
    mood_label: str
    avg_valence: float | None = Field(default=None, ge=0, le=1)
    avg_energy: float | None = Field(default=None, ge=0, le=1)
    play_count: int = Field(ge=0)
    listening_minutes: float = Field(ge=0)
    dominant_context: str
    insight: str


class ArtistMoodCallout(BaseModel):
    kind: str
    artist_name: str | None = None
    value: float | None = None
    text: str


class ArtistMoodFingerprintsResponse(BaseModel):
    period: Period
    artists: list[ArtistMoodFingerprint]
    callouts: list[ArtistMoodCallout]


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


class WeatherArtistContext(BaseModel):
    artist_id: str
    name: str
    image_url: str | None = None
    weather_category: str
    total_listens: int = Field(ge=0)
    weather_share: float = Field(ge=0, le=1)
    insight: str


class WeatherMoodShift(BaseModel):
    weather_category: str
    total_listens: int = Field(ge=0)
    listening_minutes: float = Field(ge=0)
    avg_valence: float = Field(ge=0, le=1)
    avg_energy: float = Field(ge=0, le=1)
    valence_delta: float
    energy_delta: float
    valence_percent_change: float
    energy_percent_change: float
    dominant_mood_quadrant: str
    top_artist_name: str | None = None
    insight: str
    is_strongest_shift: bool = False


class WeatherMoodHeatmapCell(BaseModel):
    weather_category: str
    mood_quadrant: str
    stream_count: int = Field(ge=0)
    listening_minutes: float = Field(ge=0)
    percentage: float = Field(ge=0, le=1)
    is_strongest: bool = False


class WeatherMoodBaseline(BaseModel):
    avg_valence: float | None = Field(default=None, ge=0, le=1)
    avg_energy: float | None = Field(default=None, ge=0, le=1)
    total_listens: int = Field(ge=0)
    listening_minutes: float = Field(ge=0)


class WeatherMoodPoint(BaseModel):
    weather_category: str
    avg_valence: float = Field(ge=0, le=1)
    avg_energy: float = Field(ge=0, le=1)
    dominant_mood_quadrant: str
    top_artist_name: str | None = None
    stream_count: int = Field(ge=0)
    listening_minutes: float = Field(ge=0)
    distance_from_overall: float = Field(ge=0)
    is_most_distinct: bool = False


class TemperatureMoodTrend(BaseModel):
    temperature_bucket: str
    avg_valence: float = Field(ge=0, le=1)
    avg_energy: float = Field(ge=0, le=1)
    stream_count: int = Field(ge=0)
    listening_minutes: float = Field(ge=0)
    is_highest_valence: bool = False
    is_highest_energy: bool = False


class WeatherCorrelationResponse(BaseModel):
    period: Period
    weather_city: str
    daily_data: list[WeatherDailyData]
    summary_by_weather: list[WeatherSummary]
    summary_by_temperature: list[WeatherSummary]
    summary_by_season: list[WeatherSummary]
    artist_weather_contexts: list[WeatherArtistContext]
    mood_baseline: WeatherMoodBaseline
    weather_mood_shifts: list[WeatherMoodShift]
    weather_mood_heatmap: list[WeatherMoodHeatmapCell]
    weather_mood_points: list[WeatherMoodPoint]
    temperature_mood_trends: list[TemperatureMoodTrend]
    weather_mood_callout: str | None = None
    temperature_mood_callout: str | None = None


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
