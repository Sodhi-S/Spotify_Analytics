from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.api.schemas import TopTracksResponse
from app.db import qualified_table
from app.services.overview import VALID_PERIODS, build_period_filter


def _params(start_date: object | None, limit: int) -> dict[str, object]:
    params: dict[str, object] = {"limit": limit}
    if start_date is not None:
        params["start_date"] = start_date
    return params


def _date_clause(start_date: object | None) -> str:
    return "" if start_date is None else "where fl.date_id >= :start_date"


def _split_tags(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [tag.strip() for tag in str(value).split(",") if tag.strip()]


class TopTracksService:
    def __init__(self, connection: Connection):
        self.connection = connection

    def get_top_tracks(self, period: str, limit: int) -> TopTracksResponse:
        period_filter = build_period_filter(period)
        sql = text(
            f"""
            select
                fl.track_id,
                coalesce(dt.name, 'Unknown Track') as name,
                coalesce(dt.artist_name, da.name, 'Unknown Artist') as artist_name,
                dt.album,
                count(*) as play_count,
                coalesce(sum(fl.ms_played), 0) as total_ms_played,
                dt.mood_label,
                dt.mood_confidence,
                dt.top_tags
            from {qualified_table("fact_listens")} fl
            left join {qualified_table("dim_tracks")} dt on fl.track_id = dt.track_id
            left join {qualified_table("dim_artists")} da
                on fl.artist_id = da.artist_id and da.is_current = true
            {_date_clause(period_filter.start_date)}
            group by
                fl.track_id,
                dt.name,
                dt.artist_name,
                da.name,
                dt.album,
                dt.mood_label,
                dt.mood_confidence,
                dt.top_tags
            order by play_count desc, name asc, artist_name asc
            limit :limit
            """
        )

        rows = self.connection.execute(
            sql,
            _params(period_filter.start_date, limit),
        ).fetchall()

        tracks: list[dict[str, Any]] = []
        for index, row in enumerate(rows, start=1):
            item = dict(row._mapping)
            item["rank"] = index
            item["play_count"] = int(item["play_count"] or 0)
            item["total_ms_played"] = int(item["total_ms_played"] or 0)
            item["top_tags"] = _split_tags(item.get("top_tags"))
            tracks.append(item)

        return TopTracksResponse(
            period=period_filter.period,
            limit=limit,
            tracks=tracks,
        )


def validate_top_tracks_params(period: str, limit: int) -> None:
    if period not in VALID_PERIODS:
        raise ValueError("Invalid period. Accepted values: 7d, 30d, 6m, all")
    if limit < 1 or limit > 50:
        raise ValueError("Limit must be between 1 and 50")
