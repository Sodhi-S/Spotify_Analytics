from __future__ import annotations

import logging
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies import get_current_user
from app.api.schemas import (
    AppSettingsResponse,
    AppSettingsUpdate,
    AuthUserResponse,
    CityOption,
    ArtistMoodFingerprintsResponse,
    DateTimeMonthDetailResponse,
    DateTimeOverviewResponse,
    OverviewResponse,
    PasswordLoginRequest,
    SetPasswordRequest,
    TopTracksResponse,
    WeatherCorrelationResponse,
)
from app.core.config import get_settings
from app.db import db_connection
from app.ingestion.lastfm import LastFmClient
from app.ingestion.openmeteo import OpenMeteoClient
from app.pipeline.user_ingestion import run_user_initial_import
from app.services.artist_mood_fingerprints import (
    ArtistMoodFingerprintService,
    validate_artist_mood_params,
)
from app.services.datetime_insights import (
    DateTimeInsightsService,
    validate_datetime_period,
    validate_year_month,
)
from app.services.overview import VALID_PERIODS, OverviewService
from app.pipeline.weather_jobs import process_weather_city
from app.services.settings import SettingsService, WeatherLocation
from app.services.top_tracks import TopTracksService, validate_top_tracks_params
from app.services.weather_correlation import (
    WeatherCorrelationService,
    validate_weather_period,
)
from app.services.auth import (
    AuthenticatedUser,
    authenticate_with_password,
    create_ingestion_job,
    create_session,
    get_or_create_user,
    latest_ingestion_job,
    new_token,
    revoke_session,
    set_user_password,
)

logger = logging.getLogger(__name__)

settings = get_settings()
app = FastAPI(title="Music Listening Intelligence API", version="0.1.0")
LASTFM_AUTH_URL = "https://www.last.fm/api/auth/"
LASTFM_AUTH_STATE_COOKIE = "lastfm_auth_state"
LASTFM_AUTH_MODE_COOKIE = "lastfm_auth_mode"
LASTFM_AUTH_MODES = {"login", "set_password"}

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


def _secure_cookie() -> bool:
    return get_settings().frontend_auth_redirect_url.startswith("https://")


def _set_session_cookie(response: Response, token: str, max_age_seconds: int) -> None:
    response.set_cookie(
        get_settings().session_cookie_name,
        token,
        max_age=max_age_seconds,
        httponly=True,
        secure=_secure_cookie(),
        samesite="lax",
        path="/",
    )


def _url_with_query_param(url: str, key: str, value: str) -> str:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query[key] = value
    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            parts.path,
            urlencode(query),
            parts.fragment,
        )
    )


def _auth_user_response(current_user: AuthenticatedUser) -> AuthUserResponse:
    with db_connection() as connection:
        job = latest_ingestion_job(connection, current_user.id)
    return AuthUserResponse(
        id=current_user.id,
        lastfm_username=current_user.lastfm_username,
        display_name=current_user.display_name,
        has_password=current_user.has_password,
        ingestion_job=job,
    )


@app.get("/api/auth/lastfm/login")
def lastfm_login(request: Request, mode: str = "login") -> RedirectResponse:
    current_settings = get_settings()
    if not current_settings.lastfm_api_key or not current_settings.lastfm_api_secret:
        raise HTTPException(
            status_code=500,
            detail="LASTFM_API_KEY and LASTFM_API_SECRET must be configured",
        )
    if mode not in LASTFM_AUTH_MODES:
        raise HTTPException(status_code=400, detail="Invalid Last.fm auth mode")

    state = new_token()
    callback_url = str(request.url_for("lastfm_callback"))
    callback_url = f"{callback_url}?state={state}"
    redirect = RedirectResponse(
        f"{LASTFM_AUTH_URL}?{urlencode({'api_key': current_settings.lastfm_api_key, 'cb': callback_url})}"
    )
    redirect.set_cookie(
        LASTFM_AUTH_STATE_COOKIE,
        state,
        max_age=600,
        httponly=True,
        secure=_secure_cookie(),
        samesite="lax",
        path="/",
    )
    redirect.set_cookie(
        LASTFM_AUTH_MODE_COOKIE,
        mode,
        max_age=600,
        httponly=True,
        secure=_secure_cookie(),
        samesite="lax",
        path="/",
    )
    return redirect


@app.get("/api/auth/lastfm/callback")
def lastfm_callback(
    request: Request,
    background_tasks: BackgroundTasks,
    token: str | None = None,
    state: str | None = None,
) -> RedirectResponse:
    state_cookie = request.cookies.get(LASTFM_AUTH_STATE_COOKIE)
    auth_mode = request.cookies.get(LASTFM_AUTH_MODE_COOKIE) or "login"
    if not token:
        raise HTTPException(status_code=400, detail="Missing Last.fm token")
    if not state_cookie or state != state_cookie:
        raise HTTPException(status_code=400, detail="Missing or invalid Last.fm login state")
    if auth_mode not in LASTFM_AUTH_MODES:
        raise HTTPException(status_code=400, detail="Invalid Last.fm login mode")

    try:
        lastfm_session = LastFmClient().get_session(token)
        username = str(lastfm_session["name"])
        with db_connection() as connection:
            user = get_or_create_user(connection, username, display_name=username)
            session_token, expires_at = create_session(connection, user.id)
            job_id = create_ingestion_job(connection, user.id)
    except Exception:
        logger.exception("Last.fm auth callback failed")
        raise HTTPException(status_code=502, detail="Unable to authenticate with Last.fm") from None

    background_tasks.add_task(
        run_user_initial_import,
        user.id,
        user.lastfm_username,
        job_id,
    )

    current_settings = get_settings()
    redirect_url = current_settings.frontend_auth_redirect_url
    if auth_mode == "set_password":
        redirect_url = _url_with_query_param(redirect_url, "set_password", "1")
    response = RedirectResponse(redirect_url)
    _set_session_cookie(
        response,
        session_token,
        max_age_seconds=current_settings.app_session_days * 24 * 60 * 60,
    )
    response.delete_cookie(LASTFM_AUTH_STATE_COOKIE, path="/")
    response.delete_cookie(LASTFM_AUTH_MODE_COOKIE, path="/")
    return response


@app.get("/api/auth/me", response_model=AuthUserResponse)
def auth_me(current_user: AuthenticatedUser = Depends(get_current_user)) -> AuthUserResponse:
    return _auth_user_response(current_user)


@app.post("/api/auth/password/login", response_model=AuthUserResponse)
def password_login(
    login: PasswordLoginRequest,
    response: Response,
) -> AuthUserResponse:
    try:
        with db_connection() as connection:
            user = authenticate_with_password(
                connection,
                login.lastfm_username,
                login.password,
            )
            if user is None:
                raise HTTPException(status_code=401, detail="Invalid username or password")
            session_token, _ = create_session(connection, user.id)
            job = latest_ingestion_job(connection, user.id)
    except HTTPException:
        raise
    except SQLAlchemyError:
        logger.exception("Database error while logging in with password")
        raise HTTPException(status_code=503, detail="Authentication service unavailable") from None

    _set_session_cookie(
        response,
        session_token,
        max_age_seconds=get_settings().app_session_days * 24 * 60 * 60,
    )
    return AuthUserResponse(
        id=user.id,
        lastfm_username=user.lastfm_username,
        display_name=user.display_name,
        has_password=user.has_password,
        ingestion_job=job,
    )


@app.post("/api/auth/password/set", response_model=AuthUserResponse)
def set_password(
    password_update: SetPasswordRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AuthUserResponse:
    try:
        with db_connection() as connection:
            updated_user = set_user_password(connection, current_user.id, password_update.password)
            job = latest_ingestion_job(connection, updated_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    except SQLAlchemyError:
        logger.exception("Database error while setting password")
        raise HTTPException(status_code=503, detail="Authentication service unavailable") from None

    return AuthUserResponse(
        id=updated_user.id,
        lastfm_username=updated_user.lastfm_username,
        display_name=updated_user.display_name,
        has_password=updated_user.has_password,
        ingestion_job=job,
    )


@app.post("/api/auth/logout")
def auth_logout(request: Request, response: Response) -> dict[str, str]:
    token = request.cookies.get(get_settings().session_cookie_name)
    if token:
        with db_connection() as connection:
            revoke_session(connection, token)
    response.delete_cookie(get_settings().session_cookie_name, path="/")
    return {"status": "ok"}


@app.get("/api/settings", response_model=AppSettingsResponse)
def get_app_settings(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AppSettingsResponse:
    try:
        with db_connection() as connection:
            return SettingsService(connection, user_id=current_user.id).get_settings()
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
def update_app_settings(
    settings_update: AppSettingsUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AppSettingsResponse:
    try:
        with db_connection() as connection:
            updated_settings = SettingsService(
                connection,
                user_id=current_user.id,
            ).update_settings(settings_update)
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
            ),
            user_id=current_user.id,
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
    ),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> OverviewResponse:
    if period not in VALID_PERIODS:
        raise HTTPException(
            status_code=400,
            detail="Invalid period. Accepted values: 7d, 30d, 6m, all",
        )

    try:
        with db_connection() as connection:
            return OverviewService(connection, user_id=current_user.id).get_overview(period)
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
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> TopTracksResponse:
    try:
        validate_top_tracks_params(period, limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

    try:
        with db_connection() as connection:
            return TopTracksService(connection, user_id=current_user.id).get_top_tracks(period, limit)
    except SQLAlchemyError:
        logger.exception("Database error while loading top tracks")
        raise HTTPException(status_code=500, detail="Internal server error") from None


@app.get("/api/moods/artist-fingerprints", response_model=ArtistMoodFingerprintsResponse)
def get_artist_mood_fingerprints(
    period: str = Query(
        default="all",
        description="Accepted values: 7d, 30d, 6m, all",
    ),
    limit: int = Query(
        default=10,
        description="Number of artists to return. Accepted range: 5 to 10.",
    ),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> ArtistMoodFingerprintsResponse:
    try:
        validate_artist_mood_params(period, limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

    try:
        with db_connection() as connection:
            return ArtistMoodFingerprintService(
                connection,
                user_id=current_user.id,
            ).get_artist_mood_fingerprints(period, limit)
    except SQLAlchemyError:
        logger.exception("Database error while loading artist mood fingerprints")
        raise HTTPException(status_code=500, detail="Internal server error") from None


@app.get("/api/weather-correlation", response_model=WeatherCorrelationResponse)
def get_weather_correlation(
    period: str = Query(
        default="all",
        description="Accepted values: 7d, 30d, 6m, all",
    ),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> WeatherCorrelationResponse:
    try:
        validate_weather_period(period)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

    try:
        with db_connection() as connection:
            return WeatherCorrelationService(
                connection,
                user_id=current_user.id,
            ).get_weather_correlation(period)
    except SQLAlchemyError:
        logger.exception("Database error while loading weather correlation")
        raise HTTPException(status_code=500, detail="Internal server error") from None


@app.get("/api/datetime/overview", response_model=DateTimeOverviewResponse)
def get_datetime_overview(
    period: str = Query(
        default="7d",
        description="Accepted values: 7d, 30d, 6m, all",
    )
) -> DateTimeOverviewResponse:
    try:
        validate_datetime_period(period)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

    try:
        with db_connection() as connection:
            return DateTimeInsightsService(connection).get_overview(period)
    except SQLAlchemyError:
        logger.exception("Database error while loading datetime overview")
        raise HTTPException(status_code=500, detail="Internal server error") from None


@app.get(
    "/api/datetime/months/{year_month}",
    response_model=DateTimeMonthDetailResponse,
)
def get_datetime_month_detail(
    year_month: str,
    period: str = Query(
        default="all",
        description="Accepted values: 7d, 30d, 6m, all",
    ),
) -> DateTimeMonthDetailResponse:
    try:
        validate_year_month(year_month)
        validate_datetime_period(period)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

    try:
        with db_connection() as connection:
            return DateTimeInsightsService(connection).get_month_detail(year_month, period)
    except SQLAlchemyError:
        logger.exception("Database error while loading datetime month detail")
        raise HTTPException(status_code=500, detail="Internal server error") from None
