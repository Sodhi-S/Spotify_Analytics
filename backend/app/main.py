from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

from app.api.schemas import (
    AppSettingsResponse,
    AppSettingsUpdate,
    CityOption,
    OverviewResponse,
    TopTracksResponse,
    WeatherCorrelationResponse,
)
from app.core.config import get_settings
from app.db import db_connection
from app.ingestion.openmeteo import OpenMeteoClient
from app.services.overview import VALID_PERIODS, OverviewService
from app.pipeline.weather_jobs import process_weather_city
from app.services.settings import SettingsService, WeatherLocation
from app.services.top_tracks import TopTracksService, validate_top_tracks_params
from app.services.weather_correlation import (
    WeatherCorrelationService,
    validate_weather_period,
)

logger = logging.getLogger(__name__)

settings = get_settings()
app = FastAPI(title="Music Listening Intelligence API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/settings", response_model=AppSettingsResponse)
def get_app_settings() -> AppSettingsResponse:
    try:
        with db_connection() as connection:
            return SettingsService(connection).get_settings()
    except SQLAlchemyError:
        logger.exception("Database error while loading settings")
        raise HTTPException(status_code=500, detail="Internal server error") from None


@app.get("/api/cities", response_model=list[CityOption])
def search_cities(
    query: str = Query(
        min_length=2,
        max_length=120,
        description="City search text. Results are limited to North America.",
    )
) -> list[CityOption]:
    try:
        return OpenMeteoClient().search_north_america_cities(query)
    except Exception:
        logger.exception("Error while searching cities")
        raise HTTPException(status_code=502, detail="Unable to search cities") from None


@app.put("/api/settings", response_model=AppSettingsResponse)
def update_app_settings(settings_update: AppSettingsUpdate) -> AppSettingsResponse:
    try:
        with db_connection() as connection:
            updated_settings = SettingsService(connection).update_settings(settings_update)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    except SQLAlchemyError:
        logger.exception("Database error while updating settings")
        raise HTTPException(status_code=500, detail="Internal server error") from None

    try:
        process_weather_city(
            WeatherLocation(
                city=updated_settings.weather_city,
                latitude=updated_settings.weather_latitude,
                longitude=updated_settings.weather_longitude,
            )
        )
        updated_settings.weather_refresh_status = "processed"
        return updated_settings
    except Exception:
        logger.exception("Error while processing weather for updated city")
        raise HTTPException(
            status_code=502,
            detail="Settings saved, but weather refresh failed",
        ) from None


@app.get("/api/stats/overview", response_model=OverviewResponse)
def get_overview(
    period: str = Query(
        default="all",
        description="Accepted values: 7d, 30d, 6m, all",
    )
) -> OverviewResponse:
    if period not in VALID_PERIODS:
        raise HTTPException(
            status_code=400,
            detail="Invalid period. Accepted values: 7d, 30d, 6m, all",
        )

    try:
        with db_connection() as connection:
            return OverviewService(connection).get_overview(period)
    except SQLAlchemyError:
        logger.exception("Database error while loading overview")
        raise HTTPException(status_code=500, detail="Internal server error") from None


@app.get("/api/top-tracks", response_model=TopTracksResponse)
def get_top_tracks(
    period: str = Query(
        default="all",
        description="Accepted values: 7d, 30d, 6m, all",
    ),
    limit: int = Query(
        default=10,
        description="Number of tracks to return. Accepted range: 1 to 50.",
    ),
) -> TopTracksResponse:
    try:
        validate_top_tracks_params(period, limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

    try:
        with db_connection() as connection:
            return TopTracksService(connection).get_top_tracks(period, limit)
    except SQLAlchemyError:
        logger.exception("Database error while loading top tracks")
        raise HTTPException(status_code=500, detail="Internal server error") from None


@app.get("/api/weather-correlation", response_model=WeatherCorrelationResponse)
def get_weather_correlation(
    period: str = Query(
        default="all",
        description="Accepted values: 7d, 30d, 6m, all",
    )
) -> WeatherCorrelationResponse:
    try:
        validate_weather_period(period)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

    try:
        with db_connection() as connection:
            return WeatherCorrelationService(connection).get_weather_correlation(period)
    except SQLAlchemyError:
        logger.exception("Database error while loading weather correlation")
        raise HTTPException(status_code=500, detail="Internal server error") from None
