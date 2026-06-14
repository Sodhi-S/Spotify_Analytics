from __future__ import annotations

from app.core.config import get_settings
from app.pipeline.lastfm_jobs import run_lastfm_ingestion
from app.pipeline.itunes_audit import export_no_itunes_preview_tracks
from app.pipeline.music2emo_jobs import run_music2emo_pipeline
from app.pipeline.weather_jobs import fetch_daily_weather, fetch_historical_weather


def main() -> None:
    settings = get_settings()
    print("Running Last.fm ingestion...")
    print(run_lastfm_ingestion())
    if settings.music2emo_run_after_ingest:
        print("Running Music2Emo preview lookup and inference...")
        print(
            run_music2emo_pipeline(
                preview_limit=settings.music2emo_preview_limit,
                inference_limit=settings.music2emo_inference_limit,
            )
        )
        print("Exporting tracks still missing iTunes previews...")
        print(export_no_itunes_preview_tracks())
    print("Running weather ingestion...")
    print(fetch_daily_weather())
    print("Running historical weather backfill for listening dates...")
    print(fetch_historical_weather())


if __name__ == "__main__":
    main()
