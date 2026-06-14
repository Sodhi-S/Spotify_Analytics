from __future__ import annotations

import argparse
import csv
from pathlib import Path

from sqlalchemy import text

from app.db import db_connection, qualified_table
from app.ingestion.itunes import ITunesClient
from app.pipeline.itunes_audit import export_no_itunes_preview_tracks
from app.pipeline.music2emo_jobs import rebuild_music2emo_models, run_music2emo_inference


DEFAULT_OVERRIDES_PATH = Path("data/manual_itunes_overrides.csv")


def _read_overrides(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as file:
        return [
            {key: (value or "").strip() for key, value in row.items()}
            for row in csv.DictReader(file)
        ]


def _resolve_preview_url(client: ITunesClient, row: dict[str, str]) -> str | None:
    if row.get("preview_url"):
        return row["preview_url"]
    if row.get("apple_music_url"):
        return client.get_preview_url_from_apple_music_url(row["apple_music_url"])
    if row.get("Itunes link"):
        return client.get_preview_url_from_apple_music_url(row["Itunes link"])
    if row.get("itunes_link"):
        return client.get_preview_url_from_apple_music_url(row["itunes_link"])
    return None


def apply_overrides(path: Path = DEFAULT_OVERRIDES_PATH) -> dict[str, int]:
    client = ITunesClient()
    rows = _read_overrides(path)
    applied = 0
    missing_preview = 0
    missing_track = 0

    with db_connection() as connection:
        for row in rows:
            preview_url = _resolve_preview_url(client, row)
            if not preview_url:
                missing_preview += 1
                continue

            if row.get("track_id"):
                result = connection.execute(
                    text(
                        f"""
                        update {qualified_table("dim_tracks")}
                        set preview_url = :preview_url
                        where track_id = :track_id
                        """
                    ),
                    {
                        "preview_url": preview_url,
                        "track_id": row["track_id"],
                    },
                )
                track_id = row["track_id"]
            else:
                result = connection.execute(
                    text(
                        f"""
                        update {qualified_table("dim_tracks")}
                        set preview_url = :preview_url
                        where lower(artist_name) = lower(:artist_name)
                          and lower(name) = lower(:track_name)
                        """
                    ),
                    {
                        "preview_url": preview_url,
                        "artist_name": row.get("artist_name", ""),
                        "track_name": row.get("track_name", ""),
                    },
                )
                track_id = None

            if result.rowcount == 0:
                missing_track += 1
                continue

            if track_id:
                connection.execute(
                    text(
                        """
                        delete from raw.track_emotion_features
                        where track_id = :track_id
                          and error_message = 'No iTunes preview found.'
                        """
                    ),
                    {"track_id": track_id},
                )
            else:
                connection.execute(
                    text(
                        f"""
                        delete from raw.track_emotion_features features
                        using {qualified_table("dim_tracks")} tracks
                        where features.track_id = tracks.track_id
                          and features.error_message = 'No iTunes preview found.'
                          and lower(tracks.artist_name) = lower(:artist_name)
                          and lower(tracks.name) = lower(:track_name)
                        """
                    ),
                    {
                        "artist_name": row.get("artist_name", ""),
                        "track_name": row.get("track_name", ""),
                    },
                )

            applied += result.rowcount

    return {
        "rows_read": len(rows),
        "applied": applied,
        "missing_preview": missing_preview,
        "missing_track": missing_track,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply manual Apple/iTunes preview overrides.")
    parser.add_argument("--path", type=Path, default=DEFAULT_OVERRIDES_PATH)
    parser.add_argument("--skip-inference", action="store_true")
    parser.add_argument("--skip-dbt", action="store_true")
    args = parser.parse_args()

    print("Applying overrides...")
    result = apply_overrides(args.path)
    print(result)

    if result["applied"] and not args.skip_inference:
        print("Running Music2Emo for overridden previews...")
        print(run_music2emo_inference(limit=result["applied"]))

    if result["applied"] and not args.skip_dbt:
        print("Rebuilding dbt mood models...")
        print(rebuild_music2emo_models())

    print("Exporting tracks still missing iTunes previews...")
    print(export_no_itunes_preview_tracks())


if __name__ == "__main__":
    main()
