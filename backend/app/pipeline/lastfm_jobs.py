from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.alerts import send_slack_alert
from app.core.config import get_settings
from app.db import db_connection
from app.ingestion.lastfm import (
    LastFmClient,
    normalize_artist_info,
    normalize_recent_track,
)
from app.ingestion.loader import RawLoader

RECENT_SOURCE = "lastfm_recent_tracks"


def _require_lastfm_settings() -> None:
    settings = get_settings()
    if not settings.lastfm_api_key or not settings.lastfm_username:
        raise RuntimeError("LASTFM_API_KEY and LASTFM_USERNAME must be configured")


def fetch_recent_tracks() -> dict[str, int]:
    _require_lastfm_settings()
    inserted = 0
    failed = 0
    seen = 0
    latest_played_at: datetime | None = None

    with db_connection() as connection:
        loader = RawLoader(connection)
        last_fetched_at = loader.get_last_fetched_at(RECENT_SOURCE)
        from_unix = int(last_fetched_at.timestamp()) if last_fetched_at else None
        client = LastFmClient()

        try:
            for payload in client.iter_recent_tracks(from_unix=from_unix):
                seen += 1
                try:
                    row = normalize_recent_track(payload)
                    if row is None:
                        continue
                    if loader.insert_recent_track(row):
                        inserted += 1
                    played_at = row["played_at"]
                    if latest_played_at is None or played_at > latest_played_at:
                        latest_played_at = played_at
                except Exception as exc:  # noqa: BLE001 - persisted for inspection.
                    failed += 1
                    loader.insert_failed("recent_tracks", payload, str(exc))
        except Exception as exc:
            send_slack_alert("recent_tracks", f"Ingestion run failed: {exc}", failed)
            raise

        if latest_played_at is not None:
            loader.upsert_last_fetched_at(RECENT_SOURCE, latest_played_at)

    if seen == 0 and get_settings().lastfm_username:
        send_slack_alert("recent_tracks", "Ingestion returned 0 rows", failed)
    if failed:
        send_slack_alert("recent_tracks", "Records written to raw.raw_failed", failed)

    return {"seen": seen, "inserted": inserted, "failed": failed}


def fetch_track_tags(limit: int = 100) -> dict[str, int]:
    _require_lastfm_settings()
    processed = 0
    failed = 0

    with db_connection() as connection:
        loader = RawLoader(connection)
        client = LastFmClient()
        for target in loader.missing_track_tag_targets(limit=limit):
            try:
                tags = client.get_track_tags(
                    target["artist_name"],
                    target["track_name"],
                )
                loader.insert_track_tags(
                    target["artist_name"],
                    target["track_name"],
                    tags,
                )
                processed += 1
            except Exception as exc:  # noqa: BLE001
                failed += 1
                loader.insert_failed("track_tags", target, str(exc))

    if failed:
        send_slack_alert("track_tags", "Records written to raw.raw_failed", failed)
    return {"processed": processed, "failed": failed}


def fetch_artist_info(limit: int = 100) -> dict[str, int]:
    _require_lastfm_settings()
    processed = 0
    failed = 0

    with db_connection() as connection:
        loader = RawLoader(connection)
        client = LastFmClient()
        for artist_name in loader.missing_artist_info_targets(limit=limit):
            try:
                artist = normalize_artist_info(client.get_artist_info(artist_name))
                loader.upsert_artist_info(artist)
                processed += 1
            except Exception as exc:  # noqa: BLE001
                failed += 1
                loader.insert_failed("artists", {"artist_name": artist_name}, str(exc))

    if failed:
        send_slack_alert("artists", "Records written to raw.raw_failed", failed)
    return {"processed": processed, "failed": failed}


def fetch_artist_tags(limit: int = 100) -> dict[str, int]:
    _require_lastfm_settings()
    processed = 0
    failed = 0

    with db_connection() as connection:
        loader = RawLoader(connection)
        client = LastFmClient()
        for artist_name in loader.missing_artist_tag_targets(limit=limit):
            try:
                tags = client.get_artist_tags(artist_name)
                loader.upsert_artist_tags(artist_name, tags)
                processed += 1
            except Exception as exc:  # noqa: BLE001
                failed += 1
                loader.insert_failed("artist_tags", {"artist_name": artist_name}, str(exc))

    if failed:
        send_slack_alert("artist_tags", "Records written to raw.raw_failed", failed)
    return {"processed": processed, "failed": failed}


def fetch_user_charts(periods: tuple[str, ...] = ("7day", "1month", "6month", "overall")) -> dict[str, int]:
    _require_lastfm_settings()
    processed = 0

    with db_connection() as connection:
        loader = RawLoader(connection)
        now = datetime.now(timezone.utc)
        last_fetched_at = loader.get_last_fetched_at("lastfm_user_charts")
        if last_fetched_at is not None and last_fetched_at.date() == now.date():
            return {"processed": 0, "skipped": 1}

        client = LastFmClient()
        for period in periods:
            for rank, artist in enumerate(client.get_top_artists(period=period), start=1):
                loader.upsert_top_artist(
                    artist_name=str(artist.get("name", "")),
                    play_count=int(artist.get("playcount") or 0),
                    rank=rank,
                    period=period,
                )
                processed += 1
            for rank, track in enumerate(client.get_top_tracks(period=period), start=1):
                artist_payload = track.get("artist")
                artist_name = (
                    artist_payload.get("name")
                    if isinstance(artist_payload, dict)
                    else str(artist_payload or "")
                )
                loader.upsert_top_track(
                    track_name=str(track.get("name", "")),
                    artist_name=artist_name,
                    play_count=int(track.get("playcount") or 0),
                    rank=rank,
                    period=period,
                )
                processed += 1

        loader.upsert_last_fetched_at("lastfm_user_charts", now)

    return {"processed": processed}


def run_lastfm_ingestion() -> dict[str, Any]:
    started_at = datetime.now(timezone.utc)
    return {
        "started_at": started_at.isoformat(),
        "recent_tracks": fetch_recent_tracks(),
        "track_tags": fetch_track_tags(),
        "artist_info": fetch_artist_info(),
        "artist_tags": fetch_artist_tags(),
    }
