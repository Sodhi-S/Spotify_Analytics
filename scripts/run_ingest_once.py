from __future__ import annotations

from app.core.config import get_settings
from app.pipeline.lastfm_jobs import run_lastfm_ingestion
from app.pipeline.image_enrichment import rebuild_image_models, run_image_enrichment
from app.pipeline.itunes_audit import export_no_itunes_preview_tracks
from app.pipeline.music2emo_jobs import run_music2emo_pipeline
from app.pipeline.weather_jobs import fetch_daily_weather, fetch_historical_weather


def main() -> None:
    settings = get_settings()

    print("Running Last.fm ingestion...")
    print(run_lastfm_ingestion())

    refreshed_models_for_new_music = False
    if settings.image_enrichment_run_after_ingest:
        print("Refreshing dbt models for newly ingested Last.fm tracks and artists...")
        print(rebuild_image_models())
        refreshed_models_for_new_music = True

        print("Running album cover and artist image enrichment...")
        print(
            run_image_enrichment(
                track_limit=settings.image_enrichment_track_limit,
                artist_limit=settings.image_enrichment_artist_limit,
                use_album_fallback=settings.image_enrichment_artist_album_fallback,
            )
        )

        print("Rebuilding dbt models with Last.fm/Deezer image URLs...")
        print(rebuild_image_models())

    if settings.music2emo_run_after_ingest:
        print("Running iTunes preview URL lookup and Music2Emo inference...")
        print(
            run_music2emo_pipeline(
                preview_limit=settings.music2emo_preview_limit,
                inference_limit=settings.music2emo_inference_limit,
                refresh_before_lookup=not refreshed_models_for_new_music,
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
