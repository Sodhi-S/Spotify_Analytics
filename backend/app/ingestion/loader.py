from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection


def _json(value: Any) -> str:
    return json.dumps(value, default=str)


class RawLoader:
    def __init__(self, connection: Connection):
        self.connection = connection

    def get_last_fetched_at(self, source: str) -> datetime | None:
        row = self.connection.execute(
            text(
                """
                select last_fetched_at
                from raw.ingestion_metadata
                where source = :source
                """
            ),
            {"source": source},
        ).first()
        return row._mapping["last_fetched_at"] if row else None

    def upsert_last_fetched_at(self, source: str, last_fetched_at: datetime) -> None:
        self.connection.execute(
            text(
                """
                insert into raw.ingestion_metadata (source, last_fetched_at, updated_at)
                values (:source, :last_fetched_at, current_timestamp)
                on conflict (source) do update set
                    last_fetched_at = excluded.last_fetched_at,
                    updated_at = current_timestamp
                """
            ),
            {"source": source, "last_fetched_at": last_fetched_at},
        )

    def insert_failed(self, source: str, payload: Any, error_message: str) -> None:
        self.connection.execute(
            text(
                """
                insert into raw.raw_failed (source, raw_payload, error_message, failed_at)
                values (:source, cast(:raw_payload as jsonb), :error_message, current_timestamp)
                """
            ),
            {
                "source": source,
                "raw_payload": _json(payload),
                "error_message": error_message[:1000],
            },
        )

    def insert_recent_track(self, row: dict[str, Any]) -> bool:
        result = self.connection.execute(
            text(
                """
                insert into raw.recent_tracks (
                    track_name, artist_name, album, played_at, track_mbid,
                    artist_mbid, raw_payload, fetched_at
                )
                values (
                    :track_name, :artist_name, :album, :played_at, :track_mbid,
                    :artist_mbid, cast(:raw_payload as jsonb), current_timestamp
                )
                on conflict (played_at, track_name, artist_name) do nothing
                """
            ),
            {**row, "raw_payload": _json(row["raw_payload"])},
        )
        return result.rowcount > 0

    def missing_track_tag_targets(self, limit: int = 100) -> list[dict[str, str]]:
        rows = self.connection.execute(
            text(
                """
                select distinct rt.track_name, rt.artist_name
                from raw.recent_tracks rt
                left join raw.track_tags tt
                    on rt.track_name = tt.track_name and rt.artist_name = tt.artist_name
                where tt.track_name is null
                order by rt.artist_name, rt.track_name
                limit :limit
                """
            ),
            {"limit": limit},
        )
        return [dict(row._mapping) for row in rows]

    def insert_track_tags(self, artist_name: str, track_name: str, tags: list[dict[str, Any]]) -> None:
        self.connection.execute(
            text(
                """
                insert into raw.track_tags (track_name, artist_name, tags, fetched_at)
                values (:track_name, :artist_name, cast(:tags as jsonb), current_timestamp)
                on conflict (track_name, artist_name) do update set
                    tags = excluded.tags,
                    fetched_at = current_timestamp
                """
            ),
            {
                "track_name": track_name,
                "artist_name": artist_name,
                "tags": _json(tags),
            },
        )

    def missing_artist_info_targets(self, limit: int = 100) -> list[str]:
        rows = self.connection.execute(
            text(
                """
                select distinct rt.artist_name
                from raw.recent_tracks rt
                left join raw.artists a on rt.artist_name = a.artist_name
                where a.artist_name is null
                order by rt.artist_name
                limit :limit
                """
            ),
            {"limit": limit},
        )
        return [row._mapping["artist_name"] for row in rows]

    def missing_artist_tag_targets(self, limit: int = 100) -> list[str]:
        rows = self.connection.execute(
            text(
                """
                select distinct rt.artist_name
                from raw.recent_tracks rt
                left join raw.artist_tags at on rt.artist_name = at.artist_name
                where at.artist_name is null
                order by rt.artist_name
                limit :limit
                """
            ),
            {"limit": limit},
        )
        return [row._mapping["artist_name"] for row in rows]

    def upsert_artist_info(self, artist: dict[str, Any]) -> None:
        self.connection.execute(
            text(
                """
                insert into raw.artists (
                    artist_name, artist_mbid, listener_count, play_count,
                    similar_artists, bio, raw_payload, fetched_at
                )
                values (
                    :artist_name, :artist_mbid, :listener_count, :play_count,
                    cast(:similar_artists as jsonb), :bio, cast(:raw_payload as jsonb),
                    current_timestamp
                )
                on conflict (artist_name) do update set
                    artist_mbid = excluded.artist_mbid,
                    listener_count = excluded.listener_count,
                    play_count = excluded.play_count,
                    similar_artists = excluded.similar_artists,
                    bio = excluded.bio,
                    raw_payload = excluded.raw_payload,
                    fetched_at = current_timestamp
                """
            ),
            {
                **artist,
                "similar_artists": _json(artist["similar_artists"]),
                "raw_payload": _json(artist["raw_payload"]),
            },
        )

    def upsert_artist_tags(self, artist_name: str, tags: list[dict[str, Any]]) -> None:
        self.connection.execute(
            text(
                """
                insert into raw.artist_tags (artist_name, tags, fetched_at)
                values (:artist_name, cast(:tags as jsonb), current_timestamp)
                on conflict (artist_name) do update set
                    tags = excluded.tags,
                    fetched_at = current_timestamp
                """
            ),
            {"artist_name": artist_name, "tags": _json(tags)},
        )

    def upsert_weather(self, row: dict[str, Any]) -> None:
        self.connection.execute(
            text(
                """
                insert into raw.weather (
                    date, city, temp_c, temp_mean_c, temp_min_c, precipitation,
                    rain, snowfall, precipitation_hours, weather_code, source, fetched_at
                )
                values (
                    :date, :city, :temp_c, :temp_mean_c, :temp_min_c, :precipitation,
                    :rain, :snowfall, :precipitation_hours, :weather_code, :source,
                    current_timestamp
                )
                on conflict (date, city) do update set
                    temp_c = excluded.temp_c,
                    temp_mean_c = excluded.temp_mean_c,
                    temp_min_c = excluded.temp_min_c,
                    precipitation = excluded.precipitation,
                    rain = excluded.rain,
                    snowfall = excluded.snowfall,
                    precipitation_hours = excluded.precipitation_hours,
                    weather_code = excluded.weather_code,
                    source = excluded.source,
                    fetched_at = current_timestamp
                """
            ),
            {
                "date": row["date"],
                "city": row["city"],
                "temp_c": row.get("temp_c"),
                "temp_mean_c": row.get("temp_mean_c"),
                "temp_min_c": row.get("temp_min_c"),
                "precipitation": row.get("precipitation"),
                "rain": row.get("rain"),
                "snowfall": row.get("snowfall"),
                "precipitation_hours": row.get("precipitation_hours"),
                "weather_code": row.get("weather_code"),
                "source": row.get("source", "open_meteo"),
            },
        )

    def upsert_top_artist(
        self,
        artist_name: str,
        play_count: int,
        rank: int,
        period: str,
    ) -> None:
        self.connection.execute(
            text(
                """
                insert into raw.top_artists (artist_name, play_count, rank, period, fetched_at)
                values (:artist_name, :play_count, :rank, :period, current_timestamp)
                on conflict (artist_name, period, rank) do update set
                    play_count = excluded.play_count,
                    fetched_at = current_timestamp
                """
            ),
            {
                "artist_name": artist_name,
                "play_count": play_count,
                "rank": rank,
                "period": period,
            },
        )

    def upsert_top_track(
        self,
        track_name: str,
        artist_name: str,
        play_count: int,
        rank: int,
        period: str,
    ) -> None:
        self.connection.execute(
            text(
                """
                insert into raw.top_tracks (
                    track_name, artist_name, play_count, rank, period, fetched_at
                )
                values (
                    :track_name, :artist_name, :play_count, :rank, :period,
                    current_timestamp
                )
                on conflict (track_name, artist_name, period, rank) do update set
                    play_count = excluded.play_count,
                    fetched_at = current_timestamp
                """
            ),
            {
                "track_name": track_name,
                "artist_name": artist_name,
                "play_count": play_count,
                "rank": rank,
                "period": period,
            },
        )
