from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - local environments may not be installed yet.
    load_dotenv = None


ROOT_DIR = Path(__file__).resolve().parents[3]


def _load_env() -> None:
    if load_dotenv is not None:
        load_dotenv(ROOT_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    lastfm_api_key: str
    lastfm_username: str
    db_connection_string: str
    warehouse_schema: str
    openmeteo_city: str
    slack_webhook_url: str | None
    target_sample_rate: int
    cors_origins: tuple[str, ...]
    mood_model_path: Path


def get_settings() -> Settings:
    _load_env()
    cors = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")
    return Settings(
        lastfm_api_key=os.getenv("LASTFM_API_KEY", ""),
        lastfm_username=os.getenv("LASTFM_USERNAME", ""),
        db_connection_string=os.getenv(
            "DB_CONNECTION_STRING",
            "postgresql+psycopg://postgres:postgres@localhost:5432/music_intelligence",
        ),
        warehouse_schema=os.getenv("WAREHOUSE_SCHEMA", ""),
        openmeteo_city=os.getenv("OPENMETEO_CITY", "Toronto"),
        slack_webhook_url=os.getenv("SLACK_WEBHOOK_URL") or None,
        target_sample_rate=int(os.getenv("TARGET_SAMPLE_RATE", "22050")),
        cors_origins=tuple(origin.strip() for origin in cors.split(",") if origin.strip()),
        mood_model_path=ROOT_DIR / os.getenv("MOOD_MODEL_PATH", "model/mood_classifier.pkl"),
    )
