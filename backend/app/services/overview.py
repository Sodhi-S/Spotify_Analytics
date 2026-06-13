from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Literal

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.api.schemas import OverviewResponse
from app.db import qualified_table

PeriodValue = Literal["7d", "30d", "6m", "all"]

VALID_PERIODS: tuple[PeriodValue, ...] = ("7d", "30d", "6m", "all")
MOOD_LABELS: tuple[str, ...] = (
    "happy",
    "sad",
    "angry",
    "calm",
    "energetic",
    "melancholic",
)


@dataclass(frozen=True)
class PeriodFilter:
    period: PeriodValue
    start_date: date | None


def build_period_filter(period: str, today: date | None = None) -> PeriodFilter:
    if period not in VALID_PERIODS:
        raise ValueError("Invalid period. Accepted values: 7d, 30d, 6m, all")

    today = today or date.today()
    offsets: dict[str, int | None] = {
        "7d": 6,
        "30d": 29,
        "6m": 179,
        "all": None,
    }
    offset = offsets[period]
    start_date = None if offset is None else today - timedelta(days=offset)
    return PeriodFilter(period=period, start_date=start_date)  # type: ignore[arg-type]


def _date_clause(column_name: str, period_filter: PeriodFilter) -> str:
    return "" if period_filter.start_date is None else f"where {column_name} >= :start_date"


def _params(period_filter: PeriodFilter) -> dict[str, Any]:
    return {} if period_filter.start_date is None else {"start_date": period_filter.start_date}


def _scalar_int(row: Any, key: str) -> int:
    if row is None:
        return 0
    value = row._mapping.get(key)
    return int(value or 0)


class OverviewService:
    def __init__(self, connection: Connection):
        self.connection = connection

    def get_overview(self, period: str) -> OverviewResponse:
        period_filter = build_period_filter(period)
        params = _params(period_filter)

        summary = self._summary(period_filter, params)
        return OverviewResponse(
            period=period_filter.period,
            total_listens=summary["total_listens"],
            unique_tracks=self._unique_count(
                "track_id", period_filter, params
            ),
            unique_artists=self._unique_count(
                "artist_id", period_filter, params
            ),
            top_tracks=self._top_tracks(period_filter, params),
            top_artists=self._top_artists(period_filter, params),
            top_tags=self._top_tags(period_filter, params),
            mood_breakdown=summary["mood_breakdown"],
        )

    def _summary(self, period_filter: PeriodFilter, params: dict[str, Any]) -> dict[str, Any]:
        mood_selects = ",\n".join(
            f"coalesce(sum(mood_{mood}_count), 0) as {mood}" for mood in MOOD_LABELS
        )
        sql = text(
            f"""
            select
                coalesce(sum(total_listens), 0) as total_listens,
                {mood_selects},
                coalesce(sum(mood_null_count), 0) as unclassified
            from {qualified_table("mart_listening_summary")}
            {_date_clause("date_id", period_filter)}
            """
        )
        row = self.connection.execute(sql, params).first()
        mood_breakdown = {mood: _scalar_int(row, mood) for mood in MOOD_LABELS}
        mood_breakdown["unclassified"] = _scalar_int(row, "unclassified")
        return {
            "total_listens": _scalar_int(row, "total_listens"),
            "mood_breakdown": mood_breakdown,
        }

    def _unique_count(
        self,
        column_name: str,
        period_filter: PeriodFilter,
        params: dict[str, Any],
    ) -> int:
        sql = text(
            f"""
            select count(distinct {column_name}) as count_value
            from {qualified_table("fact_listens")}
            {_date_clause("date_id", period_filter)}
            """
        )
        return _scalar_int(self.connection.execute(sql, params).first(), "count_value")

    def _top_tracks(
        self,
        period_filter: PeriodFilter,
        params: dict[str, Any],
    ) -> list[dict[str, Any]]:
        sql = text(
            f"""
            select
                fl.track_id,
                coalesce(dt.name, 'Unknown Track') as name,
                coalesce(dt.artist_name, da.name, 'Unknown Artist') as artist_name,
                count(*) as play_count
            from {qualified_table("fact_listens")} fl
            left join {qualified_table("dim_tracks")} dt on fl.track_id = dt.track_id
            left join {qualified_table("dim_artists")} da
                on fl.artist_id = da.artist_id and da.is_current = true
            {_date_clause("fl.date_id", period_filter)}
            group by fl.track_id, dt.name, dt.artist_name, da.name
            order by play_count desc, name asc
            limit 5
            """
        )
        return [dict(row._mapping) for row in self.connection.execute(sql, params)]

    def _top_artists(
        self,
        period_filter: PeriodFilter,
        params: dict[str, Any],
    ) -> list[dict[str, Any]]:
        sql = text(
            f"""
            select
                fl.artist_id,
                coalesce(da.name, 'Unknown Artist') as name,
                count(*) as play_count
            from {qualified_table("fact_listens")} fl
            left join {qualified_table("dim_artists")} da
                on fl.artist_id = da.artist_id and da.is_current = true
            {_date_clause("fl.date_id", period_filter)}
            group by fl.artist_id, da.name
            order by play_count desc, name asc
            limit 5
            """
        )
        return [dict(row._mapping) for row in self.connection.execute(sql, params)]

    def _top_tags(
        self,
        period_filter: PeriodFilter,
        params: dict[str, Any],
    ) -> list[dict[str, Any]]:
        sql = text(
            f"""
            select
                tag,
                coalesce(sum(listen_count), 0) as listen_count
            from {qualified_table("mart_tag_listen_counts")}
            {_date_clause("date_id", period_filter)}
            group by tag
            order by listen_count desc, tag asc
            limit 5
            """
        )
        return [dict(row._mapping) for row in self.connection.execute(sql, params)]
