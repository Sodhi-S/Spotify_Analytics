from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.api.schemas import WeatherCorrelationResponse
from app.db import qualified_table
from app.services.overview import VALID_PERIODS, build_period_filter
from app.services.settings import get_weather_city

MOOD_SCORE_SQL = """
case
    when (
        m.mood_happy_count + m.mood_sad_count + m.mood_angry_count +
        m.mood_calm_count + m.mood_energetic_count + m.mood_melancholic_count
    ) = 0 then null
    else (
        m.mood_happy_count * 0.90 +
        m.mood_energetic_count * 0.75 +
        m.mood_calm_count * 0.65 +
        m.mood_melancholic_count * 0.35 +
        m.mood_sad_count * 0.20 +
        m.mood_angry_count * 0.15
    ) / (
        m.mood_happy_count + m.mood_sad_count + m.mood_angry_count +
        m.mood_calm_count + m.mood_energetic_count + m.mood_melancholic_count
    )
end
"""

CLASSIFIED_LISTENS_SQL = """
(
    m.mood_happy_count + m.mood_sad_count + m.mood_angry_count +
    m.mood_calm_count + m.mood_energetic_count + m.mood_melancholic_count
)
"""


def _params(start_date: object | None) -> dict[str, object]:
    return {} if start_date is None else {"start_date": start_date}


def _float_or_none(value: Any) -> float | None:
    return None if value is None else float(value)


def _top_tags_by_group(
    connection: Connection,
    group_column: str,
    start_date: object | None,
    weather_city: str,
) -> dict[str, list[dict[str, Any]]]:
    date_filter = "and tags.date_id >= :start_date" if start_date is not None else ""
    sql = text(
        f"""
        select
            dw.{group_column} as label,
            tags.tag,
            sum(tags.listen_count) as listen_count
        from {qualified_table("mart_tag_listen_counts")} tags
        join {qualified_table("dim_weather")} dw on tags.date_id = dw.date_id
        where dw.city = :weather_city
        {date_filter}
        group by dw.{group_column}, tags.tag
        order by dw.{group_column}, listen_count desc, tags.tag asc
        """
    )
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in connection.execute(
        sql,
        {**_params(start_date), "weather_city": weather_city},
    ):
        item = dict(row._mapping)
        label = str(item["label"] or "Unknown")
        if len(grouped[label]) < 5:
            grouped[label].append(
                {
                    "tag": item["tag"],
                    "listen_count": int(item["listen_count"] or 0),
                }
            )
    return dict(grouped)


class WeatherCorrelationService:
    def __init__(self, connection: Connection):
        self.connection = connection

    def get_weather_correlation(self, period: str) -> WeatherCorrelationResponse:
        period_filter = build_period_filter(period)
        start_date = period_filter.start_date
        weather_city = get_weather_city(self.connection)
        daily_data = self._daily_data(start_date, weather_city)
        return WeatherCorrelationResponse(
            period=period_filter.period,
            weather_city=weather_city,
            daily_data=daily_data,
            summary_by_weather=self._summary("weather_category", start_date, weather_city),
            summary_by_temperature=self._summary("temperature_bucket", start_date, weather_city),
            summary_by_season=self._summary("season", start_date, weather_city),
        )

    def _daily_data(self, start_date: object | None, weather_city: str) -> list[dict[str, Any]]:
        date_filter = "and m.date_id >= :start_date" if start_date is not None else ""
        sql = text(
            f"""
            select
                d.date_id,
                d.day_of_week,
                d.is_weekend,
                m.total_listens,
                {MOOD_SCORE_SQL} as mood_score,
                m.mood_happy_count,
                m.mood_sad_count,
                m.mood_angry_count,
                m.mood_calm_count,
                m.mood_energetic_count,
                m.mood_melancholic_count,
                m.mood_null_count,
                dw.temp_c,
                dw.temp_min_c,
                dw.temp_mean_c,
                dw.precipitation,
                dw.rain,
                dw.snowfall,
                dw.precipitation_hours,
                dw.weather_code,
                dw.weather_category,
                dw.temperature_bucket,
                dw.season,
                dw.had_precipitation
            from {qualified_table("mart_listening_summary")} m
            join {qualified_table("dim_dates")} d on m.date_id = d.date_id
            join {qualified_table("dim_weather")} dw on m.date_id = dw.date_id
            where dw.city = :weather_city
            {date_filter}
            order by d.date_id asc
            """
        )

        rows: list[dict[str, Any]] = []
        for row in self.connection.execute(
            sql,
            {**_params(start_date), "weather_city": weather_city},
        ):
            item = row._mapping
            rows.append(
                {
                    "date": item["date_id"].isoformat(),
                    "day_of_week": item["day_of_week"],
                    "is_weekend": item["is_weekend"],
                    "total_listens": int(item["total_listens"] or 0),
                    "mood_score": _float_or_none(item["mood_score"]),
                    "mood_distribution": {
                        "happy": int(item["mood_happy_count"] or 0),
                        "sad": int(item["mood_sad_count"] or 0),
                        "angry": int(item["mood_angry_count"] or 0),
                        "calm": int(item["mood_calm_count"] or 0),
                        "energetic": int(item["mood_energetic_count"] or 0),
                        "melancholic": int(item["mood_melancholic_count"] or 0),
                        "unclassified": int(item["mood_null_count"] or 0),
                    },
                    "temp_c": _float_or_none(item["temp_mean_c"]),
                    "temp_min_c": _float_or_none(item["temp_min_c"]),
                    "temp_max_c": _float_or_none(item["temp_c"]),
                    "precipitation": _float_or_none(item["precipitation"]),
                    "rain": _float_or_none(item["rain"]),
                    "snowfall": _float_or_none(item["snowfall"]),
                    "precipitation_hours": _float_or_none(item["precipitation_hours"]),
                    "weather_code": item["weather_code"],
                    "weather_category": item["weather_category"],
                    "temperature_bucket": item["temperature_bucket"],
                    "season": item["season"],
                    "had_precipitation": item["had_precipitation"],
                }
            )
        return rows

    def _summary(
        self,
        group_column: str,
        start_date: object | None,
        weather_city: str,
    ) -> list[dict[str, Any]]:
        top_tags = _top_tags_by_group(self.connection, group_column, start_date, weather_city)
        date_filter = "and m.date_id >= :start_date" if start_date is not None else ""
        sql = text(
            f"""
            select
                dw.{group_column} as label,
                count(distinct m.date_id) as total_days,
                coalesce(sum(m.total_listens), 0) as total_listens,
                case
                    when count(distinct m.date_id) = 0 then 0
                    else coalesce(sum(m.total_listens), 0)::numeric / count(distinct m.date_id)
                end as avg_listens_per_day,
                case
                    when sum({CLASSIFIED_LISTENS_SQL}) = 0 then null
                    else sum(({MOOD_SCORE_SQL}) * {CLASSIFIED_LISTENS_SQL}) / sum({CLASSIFIED_LISTENS_SQL})
                end as avg_mood_score,
                avg(dw.temp_mean_c) as avg_temp_c,
                coalesce(sum(dw.precipitation), 0) as total_precipitation
            from {qualified_table("mart_listening_summary")} m
            join {qualified_table("dim_weather")} dw on m.date_id = dw.date_id
            where dw.city = :weather_city
            {date_filter}
            group by dw.{group_column}
            order by total_listens desc, label asc
            """
        )

        summaries: list[dict[str, Any]] = []
        for row in self.connection.execute(
            sql,
            {**_params(start_date), "weather_city": weather_city},
        ):
            item = row._mapping
            label = str(item["label"] or "Unknown")
            summaries.append(
                {
                    "label": label,
                    "total_days": int(item["total_days"] or 0),
                    "total_listens": int(item["total_listens"] or 0),
                    "avg_listens_per_day": float(item["avg_listens_per_day"] or 0),
                    "avg_mood_score": _float_or_none(item["avg_mood_score"]),
                    "avg_temp_c": _float_or_none(item["avg_temp_c"]),
                    "total_precipitation": float(item["total_precipitation"] or 0),
                    "top_tags": top_tags.get(label, []),
                }
            )
        return summaries


def validate_weather_period(period: str) -> None:
    if period not in VALID_PERIODS:
        raise ValueError("Invalid period. Accepted values: 7d, 30d, 6m, all")
