from __future__ import annotations

import csv
from pathlib import Path

from sqlalchemy import text

from app.core.config import ROOT_DIR
from app.db import db_connection, qualified_table

DEFAULT_NO_ITUNES_EXPORT_PATH = ROOT_DIR / "exports" / "no_itunes_preview_tracks.csv"


def export_no_itunes_preview_tracks(
    output_path: Path = DEFAULT_NO_ITUNES_EXPORT_PATH,
) -> dict[str, object]:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with db_connection() as connection:
        rows = connection.execute(
            text(
                f"""
                select
                    dt.track_id,
                    dt.artist_name,
                    dt.name as track_name,
                    dt.album,
                    count(fl.listen_id) as listen_count,
                    min(fl.played_at) as first_played_at,
                    max(fl.played_at) as last_played_at
                from raw.track_emotion_features ef
                join {qualified_table("dim_tracks")} dt
                    on dt.track_id = ef.track_id
                left join {qualified_table("fact_listens")} fl
                    on fl.track_id = dt.track_id
                where ef.error_message = 'No iTunes preview found.'
                  and dt.preview_url is null
                group by dt.track_id, dt.artist_name, dt.name, dt.album
                order by listen_count desc, dt.artist_name, dt.name
                """
            )
        ).fetchall()

    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "track_id",
                "artist_name",
                "track_name",
                "album",
                "listen_count",
                "first_played_at",
                "last_played_at",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row._mapping))

    return {
        "path": str(output_path),
        "rows": len(rows),
    }
