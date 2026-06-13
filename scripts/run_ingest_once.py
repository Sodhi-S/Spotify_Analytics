from __future__ import annotations

from app.pipeline.lastfm_jobs import run_lastfm_ingestion
from app.pipeline.weather_jobs import fetch_daily_weather


def main() -> None:
    print("Running Last.fm ingestion...")
    print(run_lastfm_ingestion())
    print("Running weather ingestion...")
    print(fetch_daily_weather())


if __name__ == "__main__":
    main()
