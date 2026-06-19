from __future__ import annotations

import re
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.api.schemas import DateTimeMonthDetailResponse, DateTimeOverviewResponse
from app.db import qualified_table
from app.services.overview import VALID_PERIODS, PeriodFilter, build_period_filter

DAY_ORDER = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
YEAR_MONTH_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")

TIME_SEGMENTS: tuple[tuple[str, int, int], ...] = (
    ("Late Night", 0, 4),
    ("Morning", 5, 11),
    ("Afternoon", 12, 16),
    ("Evening", 17, 21),
    ("Night", 22, 23),
)

# Aggregate fragments shared across the time-bucket queries. Averages exclude
# null valence/energy; dominant mood ignores unclassified tracks (counted as the
# mode only over non-null mood labels).
MOOD_AGG_SQL = """
    avg(valence) filter (where valence is not null) as avg_valence,
    avg(energy) filter (where energy is not null) as avg_energy,
    mode() within group (order by mood_label)
        filter (where mood_label is not null) as dominant_mood
"""


def _time_segment(hour: int) -> str:
    for label, start, end in TIME_SEGMENTS:
        if start <= hour <= end:
            return label
    return "Night"


def _float_or_none(value: Any) -> float | None:
    return None if value is None else float(value)


def _date_clause(alias_column: str, period_filter: PeriodFilter) -> str:
    return "" if period_filter.start_date is None else f"and {alias_column} >= :start_date"


def _params(period_filter: PeriodFilter, **extra: Any) -> dict[str, Any]:
    params: dict[str, Any] = dict(extra)
    if period_filter.start_date is not None:
        params["start_date"] = period_filter.start_date
    return params


class DateTimeInsightsService:
    def __init__(self, connection: Connection):
        self.connection = connection
        self.table = qualified_table("mart_datetime_listens")

    def get_overview(self, period: str) -> DateTimeOverviewResponse:
        period_filter = build_period_filter(period)
        params = _params(period_filter)
        date_clause = _date_clause("local_date", period_filter)

        monthly = self._monthly(date_clause, params)
        days = self._days(date_clause, params)
        hours = self._hours(date_clause, params)
        heatmap = self._heatmap(date_clause, params)
        segments = self._segment_averages(date_clause, params)

        total_listens = sum(bucket["total_listens"] for bucket in monthly)

        return DateTimeOverviewResponse(
            period=period_filter.period,
            total_listens=total_listens,
            most_active_month=_top_label(monthly, "year_month"),
            most_active_day=_top_label(days, "day_of_week"),
            most_active_hour=_top_label(hours, "hour"),
            highest_energy_bucket=_top_segment(segments, "avg_energy"),
            highest_valence_bucket=_top_segment(segments, "avg_valence"),
            monthly=monthly,
            days=days,
            hours=hours,
            heatmap=heatmap,
        )

    def _monthly(self, date_clause: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        top_artists = self._top_artist_by_group("year_month", date_clause, params)
        sql = text(
            f"""
            select
                local_year as year,
                local_month as month,
                year_month,
                count(*) as total_listens,
                count(distinct track_id) as unique_tracks,
                count(distinct artist_id) as unique_artists,
                {MOOD_AGG_SQL}
            from {self.table}
            where 1 = 1
            {date_clause}
            group by local_year, local_month, year_month
            order by local_year asc, local_month asc
            """
        )
        buckets: list[dict[str, Any]] = []
        for row in self.connection.execute(sql, params):
            item = row._mapping
            buckets.append(
                {
                    "year": int(item["year"]),
                    "month": int(item["month"]),
                    "year_month": item["year_month"],
                    "total_listens": int(item["total_listens"] or 0),
                    "unique_tracks": int(item["unique_tracks"] or 0),
                    "unique_artists": int(item["unique_artists"] or 0),
                    "avg_valence": _float_or_none(item["avg_valence"]),
                    "avg_energy": _float_or_none(item["avg_energy"]),
                    "dominant_mood": item["dominant_mood"],
                    "top_artist_name": top_artists.get(item["year_month"]),
                }
            )
        return buckets

    def _days(self, date_clause: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        top_artists = self._top_artist_by_group("day_of_week", date_clause, params)
        sql = text(
            f"""
            select
                day_of_week,
                dow_num,
                bool_or(is_weekend) as is_weekend,
                count(*) as total_listens,
                {MOOD_AGG_SQL}
            from {self.table}
            where 1 = 1
            {date_clause}
            group by day_of_week, dow_num
            order by dow_num asc
            """
        )
        days: list[dict[str, Any]] = []
        for row in self.connection.execute(sql, params):
            item = row._mapping
            days.append(
                {
                    "day_of_week": item["day_of_week"],
                    "total_listens": int(item["total_listens"] or 0),
                    "avg_valence": _float_or_none(item["avg_valence"]),
                    "avg_energy": _float_or_none(item["avg_energy"]),
                    "dominant_mood": item["dominant_mood"],
                    "top_artist_name": top_artists.get(item["day_of_week"]),
                    "is_weekend": bool(item["is_weekend"]),
                }
            )
        return days

    def _hours(self, date_clause: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        sql = text(
            f"""
            select
                local_hour as hour,
                count(*) as total_listens,
                {MOOD_AGG_SQL}
            from {self.table}
            where 1 = 1
            {date_clause}
            group by local_hour
            """
        )
        by_hour = {int(row._mapping["hour"]): row._mapping for row in self.connection.execute(sql, params)}
        hours: list[dict[str, Any]] = []
        for hour in range(24):
            item = by_hour.get(hour)
            hours.append(
                {
                    "hour": hour,
                    "time_segment": _time_segment(hour),
                    "total_listens": int(item["total_listens"] or 0) if item else 0,
                    "avg_valence": _float_or_none(item["avg_valence"]) if item else None,
                    "avg_energy": _float_or_none(item["avg_energy"]) if item else None,
                    "dominant_mood": item["dominant_mood"] if item else None,
                }
            )
        return hours

    def _heatmap(self, date_clause: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        sql = text(
            f"""
            select
                day_of_week,
                dow_num,
                local_hour as hour,
                count(*) as total_listens,
                {MOOD_AGG_SQL}
            from {self.table}
            where 1 = 1
            {date_clause}
            group by day_of_week, dow_num, local_hour
            """
        )
        by_cell: dict[tuple[str, int], Any] = {}
        for row in self.connection.execute(sql, params):
            item = row._mapping
            by_cell[(item["day_of_week"], int(item["hour"]))] = item

        cells: list[dict[str, Any]] = []
        for day in DAY_ORDER:
            for hour in range(24):
                item = by_cell.get((day, hour))
                cells.append(
                    {
                        "day_of_week": day,
                        "hour": hour,
                        "total_listens": int(item["total_listens"] or 0) if item else 0,
                        "avg_valence": _float_or_none(item["avg_valence"]) if item else None,
                        "avg_energy": _float_or_none(item["avg_energy"]) if item else None,
                        "dominant_mood": item["dominant_mood"] if item else None,
                    }
                )
        return cells

    def _segment_averages(self, date_clause: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        sql = text(
            f"""
            select
                case
                    when local_hour between 0 and 4 then 'Late Night'
                    when local_hour between 5 and 11 then 'Morning'
                    when local_hour between 12 and 16 then 'Afternoon'
                    when local_hour between 17 and 21 then 'Evening'
                    else 'Night'
                end as segment,
                count(*) as total_listens,
                avg(valence) filter (where valence is not null) as avg_valence,
                avg(energy) filter (where energy is not null) as avg_energy
            from {self.table}
            where 1 = 1
            {date_clause}
            group by segment
            """
        )
        return [
            {
                "segment": row._mapping["segment"],
                "total_listens": int(row._mapping["total_listens"] or 0),
                "avg_valence": _float_or_none(row._mapping["avg_valence"]),
                "avg_energy": _float_or_none(row._mapping["avg_energy"]),
            }
            for row in self.connection.execute(sql, params)
        ]

    def _top_artist_by_group(
        self,
        group_column: str,
        date_clause: str,
        params: dict[str, Any],
    ) -> dict[Any, str]:
        sql = text(
            f"""
            with grouped as (
                select
                    {group_column} as label,
                    coalesce(artist_name, 'Unknown Artist') as artist_name,
                    count(*) as play_count
                from {self.table}
                where 1 = 1
                {date_clause}
                group by {group_column}, artist_name
            ),
            ranked as (
                select
                    label,
                    artist_name,
                    row_number() over (
                        partition by label
                        order by play_count desc, artist_name asc
                    ) as artist_rank
                from grouped
            )
            select label, artist_name
            from ranked
            where artist_rank = 1
            """
        )
        return {
            row._mapping["label"]: row._mapping["artist_name"]
            for row in self.connection.execute(sql, params)
        }

    def get_month_detail(self, year_month: str, period: str) -> DateTimeMonthDetailResponse:
        period_filter = build_period_filter(period)
        date_clause = _date_clause("local_date", period_filter)
        params = _params(period_filter, year_month=year_month)

        summary_row = self.connection.execute(
            text(
                f"""
                select
                    count(*) as total_listens,
                    count(distinct track_id) as unique_tracks,
                    count(distinct artist_id) as unique_artists,
                    {MOOD_AGG_SQL}
                from {self.table}
                where year_month = :year_month
                {date_clause}
                """
            ),
            params,
        ).one()._mapping

        total_listens = int(summary_row["total_listens"] or 0)
        avg_valence = _float_or_none(summary_row["avg_valence"])
        avg_energy = _float_or_none(summary_row["avg_energy"])
        dominant_mood = summary_row["dominant_mood"]

        top_tracks = self._month_top_tracks(date_clause, params)
        top_artists = self._month_top_artists(date_clause, params)
        top_tags = self._month_top_tags(year_month, period_filter)

        return DateTimeMonthDetailResponse(
            year_month=year_month,
            total_listens=total_listens,
            unique_tracks=int(summary_row["unique_tracks"] or 0),
            unique_artists=int(summary_row["unique_artists"] or 0),
            avg_valence=avg_valence,
            avg_energy=avg_energy,
            dominant_mood=dominant_mood,
            top_tracks=top_tracks,
            top_artists=top_artists,
            top_tags=top_tags,
            summary=_month_summary(
                year_month,
                total_listens,
                avg_valence,
                avg_energy,
                dominant_mood,
                top_artists[0]["name"] if top_artists else None,
                top_tags[0]["tag"] if top_tags else None,
            ),
        )

    def _month_top_tracks(self, date_clause: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        sql = text(
            f"""
            select
                track_id,
                coalesce(min(track_name), 'Unknown Track') as name,
                coalesce(min(artist_name), 'Unknown Artist') as artist_name,
                min(album_image_url) as album_image_url,
                count(*) as play_count
            from {self.table}
            where year_month = :year_month
            {date_clause}
            group by track_id
            order by play_count desc, name asc
            limit 10
            """
        )
        return [
            {
                "track_id": row._mapping["track_id"],
                "name": row._mapping["name"],
                "artist_name": row._mapping["artist_name"],
                "play_count": int(row._mapping["play_count"] or 0),
                "album_image_url": row._mapping["album_image_url"],
            }
            for row in self.connection.execute(sql, params)
        ]

    def _month_top_artists(self, date_clause: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        sql = text(
            f"""
            select
                dl.artist_id,
                coalesce(da.name, min(dl.artist_name), 'Unknown Artist') as name,
                da.image_url,
                count(*) as play_count
            from {self.table} dl
            left join {qualified_table("dim_artists")} da
                on dl.artist_id = da.artist_id and da.is_current = true
            where dl.year_month = :year_month
            {date_clause.replace("local_date", "dl.local_date")}
            group by dl.artist_id, da.name, da.image_url
            order by play_count desc, name asc
            limit 10
            """
        )
        return [
            {
                "artist_id": row._mapping["artist_id"],
                "name": row._mapping["name"],
                "play_count": int(row._mapping["play_count"] or 0),
                "image_url": row._mapping["image_url"],
            }
            for row in self.connection.execute(sql, params)
        ]

    def _month_top_tags(
        self,
        year_month: str,
        period_filter: PeriodFilter,
    ) -> list[dict[str, Any]]:
        date_clause = _date_clause("date_id", period_filter)
        sql = text(
            f"""
            select
                tag,
                coalesce(sum(listen_count), 0) as listen_count
            from {qualified_table("mart_tag_listen_counts")}
            where to_char(date_id, 'YYYY-MM') = :year_month
            {date_clause}
            group by tag
            order by listen_count desc, tag asc
            limit 10
            """
        )
        params = _params(period_filter, year_month=year_month)
        return [
            {
                "tag": row._mapping["tag"],
                "listen_count": int(row._mapping["listen_count"] or 0),
            }
            for row in self.connection.execute(sql, params)
        ]


def _top_label(buckets: list[dict[str, Any]], label_key: str) -> Any:
    if not buckets:
        return None
    best = max(buckets, key=lambda bucket: bucket["total_listens"])
    return None if best["total_listens"] == 0 else best[label_key]


def _top_segment(segments: list[dict[str, Any]], metric: str) -> str | None:
    candidates = [segment for segment in segments if segment[metric] is not None]
    if not candidates:
        return None
    return max(candidates, key=lambda segment: segment[metric])["segment"]


def _format_year_month(year_month: str) -> str:
    months = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ]
    try:
        year, month = year_month.split("-")
        return f"{months[int(month) - 1]} {year}"
    except (ValueError, IndexError):
        return year_month


def _month_summary(
    year_month: str,
    total_listens: int,
    avg_valence: float | None,
    avg_energy: float | None,
    dominant_mood: str | None,
    top_artist: str | None,
    top_tag: str | None,
) -> str:
    label = _format_year_month(year_month)
    if total_listens == 0:
        return f"No listening recorded in {label} for this period yet."

    if avg_energy is not None and avg_energy >= 0.6:
        energy_text = "a high-energy month"
    elif avg_energy is not None and avg_energy < 0.4:
        energy_text = "a low-energy month"
    elif avg_valence is not None and avg_valence >= 0.6:
        energy_text = "a bright month"
    elif avg_valence is not None and avg_valence < 0.4:
        energy_text = "a darker month"
    else:
        energy_text = "a balanced month"

    parts = [f"{label} was {energy_text}"]
    if top_artist:
        parts.append(f"led by {top_artist}")
    if top_tag:
        parts.append(f"with {top_tag} on heavy rotation")
    sentence = ", ".join(parts) + "."
    if dominant_mood:
        sentence += f" Most tracks landed in {dominant_mood} territory."
    return sentence


def validate_datetime_period(period: str) -> None:
    if period not in VALID_PERIODS:
        raise ValueError("Invalid period. Accepted values: 7d, 30d, 6m, all")


def validate_year_month(year_month: str) -> None:
    if not YEAR_MONTH_PATTERN.match(year_month):
        raise ValueError("Invalid month. Expected format: YYYY-MM")
