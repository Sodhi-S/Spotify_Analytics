from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.db import qualified_table


def _json(value: Any) -> str:
    return json.dumps(value, default=str)


class RawLoader:
    def __init__(self, connection: Connection):
        self.connection = connection

    def ensure_image_enrichment_tables(self) -> None:
        self.connection.execute(
            text(
                """
                create table if not exists raw.track_image_enrichments (
                    track_id text primary key,
                    album_image_url text,
                    album_image_source text,
                    album_image_width integer,
                    album_image_height integer,
                    album_image_updated_at timestamptz,
                    raw_payload jsonb not null default '{}'::jsonb,
                    unresolved_reason text,
                    attempted_at timestamptz not null default current_timestamp
                )
                """
            )
        )
        self.connection.execute(
            text(
                """
                create table if not exists raw.artist_image_enrichments (
                    artist_id text primary key,
                    image_url text,
                    image_source text,
                    image_width integer,
                    image_height integer,
                    image_updated_at timestamptz,
                    raw_payload jsonb not null default '{}'::jsonb,
                    unresolved_reason text,
                    attempted_at timestamptz not null default current_timestamp
                )
                """
            )
        )

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

    def missing_track_image_targets(
        self,
        limit: int = 100,
        refresh: bool = False,
        retry_unresolved: bool = False,
    ) -> list[dict[str, Any]]:
        if refresh:
            image_filter = ""
        elif retry_unresolved:
            image_filter = "where images.album_image_url is null"
        else:
            image_filter = "where images.track_id is null"
        rows = self.connection.execute(
            text(
                f"""
                select
                    tracks.track_id,
                    tracks.name as track_name,
                    tracks.artist_name,
                    tracks.album,
                    raw_track.raw_payload
                from {qualified_table("dim_tracks")} tracks
                left join raw.track_image_enrichments images
                    on tracks.track_id = images.track_id
                left join lateral (
                    select recent.raw_payload
                    from raw.recent_tracks recent
                    where lower(recent.track_name) = lower(tracks.name)
                      and lower(recent.artist_name) = lower(tracks.artist_name)
                      and recent.raw_payload ? 'image'
                    order by recent.played_at desc
                    limit 1
                ) raw_track on true
                {image_filter}
                order by images.attempted_at asc nulls first, tracks.artist_name, tracks.name
                limit :limit
                """
            ),
            {"limit": limit},
        )
        return [dict(row._mapping) for row in rows]

    def count_track_image_targets(self, refresh: bool = False, retry_unresolved: bool = False) -> int:
        if refresh:
            image_filter = ""
        elif retry_unresolved:
            image_filter = "where images.album_image_url is null"
        else:
            image_filter = "where images.track_id is null"
        return int(
            self.connection.execute(
                text(
                    f"""
                    select count(*) as count_value
                    from {qualified_table("dim_tracks")} tracks
                    left join raw.track_image_enrichments images
                        on tracks.track_id = images.track_id
                    {image_filter}
                    """
                )
            ).scalar_one()
            or 0
        )

    def missing_artist_image_targets(
        self,
        limit: int = 100,
        refresh: bool = False,
        retry_unresolved: bool = False,
    ) -> list[dict[str, Any]]:
        if refresh:
            image_filter = ""
        elif retry_unresolved:
            image_filter = "where images.image_url is null"
        else:
            image_filter = "where images.artist_id is null"
        rows = self.connection.execute(
            text(
                f"""
                select
                    artists.artist_id,
                    artists.name as artist_name,
                    raw_artists.raw_payload
                from {qualified_table("dim_artists")} artists
                left join raw.artist_image_enrichments images
                    on artists.artist_id = images.artist_id
                left join lateral (
                    select raw_artist.raw_payload
                    from raw.artists raw_artist
                    where lower(artists.name) = lower(raw_artist.artist_name)
                    order by raw_artist.fetched_at desc
                    limit 1
                ) raw_artists on true
                {image_filter}
                  {"where" if refresh else "and"} artists.is_current = true
                order by images.attempted_at asc nulls first, artists.name
                limit :limit
                """
            ),
            {"limit": limit},
        )
        return [dict(row._mapping) for row in rows]

    def count_artist_image_targets(self, refresh: bool = False, retry_unresolved: bool = False) -> int:
        if refresh:
            image_filter = ""
        elif retry_unresolved:
            image_filter = "where images.image_url is null"
        else:
            image_filter = "where images.artist_id is null"
        return int(
            self.connection.execute(
                text(
                    f"""
                    select count(*) as count_value
                    from {qualified_table("dim_artists")} artists
                    left join raw.artist_image_enrichments images
                        on artists.artist_id = images.artist_id
                    {image_filter}
                      {"where" if refresh else "and"} artists.is_current = true
                    """
                )
            ).scalar_one()
            or 0
        )

    def artist_album_image_fallback(self, artist_id: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            text(
                f"""
                select
                    images.album_image_url as image_url,
                    images.album_image_width as image_width,
                    images.album_image_height as image_height,
                    images.raw_payload
                from {qualified_table("dim_tracks")} tracks
                join raw.track_image_enrichments images
                    on tracks.track_id = images.track_id
                where tracks.artist_id = :artist_id
                  and images.album_image_url is not null
                order by tracks.name
                limit 1
                """
            ),
            {"artist_id": artist_id},
        ).first()
        return dict(row._mapping) if row else None

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

    def upsert_track_image(
        self,
        track_id: str,
        image_url: str | None,
        source: str | None,
        width: int | None,
        height: int | None,
        raw_payload: dict[str, Any] | None = None,
        unresolved_reason: str | None = None,
    ) -> None:
        self.connection.execute(
            text(
                """
                insert into raw.track_image_enrichments (
                    track_id, album_image_url, album_image_source, album_image_width,
                    album_image_height, album_image_updated_at, raw_payload,
                    unresolved_reason, attempted_at
                )
                values (
                    :track_id, cast(:image_url as text), :source, :width, :height,
                    case when cast(:image_url as text) is null then null else current_timestamp end,
                    cast(:raw_payload as jsonb), :unresolved_reason, current_timestamp
                )
                on conflict (track_id) do update set
                    album_image_url = excluded.album_image_url,
                    album_image_source = excluded.album_image_source,
                    album_image_width = excluded.album_image_width,
                    album_image_height = excluded.album_image_height,
                    album_image_updated_at = excluded.album_image_updated_at,
                    raw_payload = excluded.raw_payload,
                    unresolved_reason = excluded.unresolved_reason,
                    attempted_at = current_timestamp
                """
            ),
            {
                "track_id": track_id,
                "image_url": image_url,
                "source": source,
                "width": width,
                "height": height,
                "raw_payload": _json(raw_payload or {}),
                "unresolved_reason": unresolved_reason,
            },
        )

    def upsert_artist_image(
        self,
        artist_id: str,
        image_url: str | None,
        source: str | None,
        width: int | None,
        height: int | None,
        raw_payload: dict[str, Any] | None = None,
        unresolved_reason: str | None = None,
    ) -> None:
        self.connection.execute(
            text(
                """
                insert into raw.artist_image_enrichments (
                    artist_id, image_url, image_source, image_width,
                    image_height, image_updated_at, raw_payload,
                    unresolved_reason, attempted_at
                )
                values (
                    :artist_id, cast(:image_url as text), :source, :width, :height,
                    case when cast(:image_url as text) is null then null else current_timestamp end,
                    cast(:raw_payload as jsonb), :unresolved_reason, current_timestamp
                )
                on conflict (artist_id) do update set
                    image_url = excluded.image_url,
                    image_source = excluded.image_source,
                    image_width = excluded.image_width,
                    image_height = excluded.image_height,
                    image_updated_at = excluded.image_updated_at,
                    raw_payload = excluded.raw_payload,
                    unresolved_reason = excluded.unresolved_reason,
                    attempted_at = current_timestamp
                """
            ),
            {
                "artist_id": artist_id,
                "image_url": image_url,
                "source": source,
                "width": width,
                "height": height,
                "raw_payload": _json(raw_payload or {}),
                "unresolved_reason": unresolved_reason,
            },
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
