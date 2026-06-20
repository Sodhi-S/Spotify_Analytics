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

MOOD_QUADRANT_SQL = """
case
    when dt.valence >= 0.5 and dt.energy >= 0.5 then 'Happy / Hype'
    when dt.valence >= 0.5 and dt.energy < 0.5 then 'Calm / Chill'
    when dt.valence < 0.5 and dt.energy < 0.5 then 'Sad / Reflective'
    else 'Intense / Dark'
end
"""

EFFECTIVE_MS_PLAYED_SQL = "coalesce(nullif(fl.ms_played, 0), 180000)"

MOOD_QUADRANTS = ("Happy / Hype", "Calm / Chill", "Sad / Reflective", "Intense / Dark")
WEATHER_ORDER = (
    "Clear",
    "Cloudy",
    "Fog",
    "Drizzle",
    "Rain",
    "Showers",
    "Thunderstorm",
    "Freezing Rain",
    "Snow",
    "Snow Showers",
)
TEMPERATURE_ORDER = ("Freezing", "Cold", "Mild", "Warm", "Hot", "Unknown")


def _params(start_date: object | None, user_id: str) -> dict[str, object]:
    params: dict[str, object] = {"user_id": user_id}
    if start_date is not None:
        params["start_date"] = start_date
    return params


def _float_or_none(value: Any) -> float | None:
    return None if value is None else float(value)


def _weather_sort_key(label: str) -> tuple[int, str]:
    try:
        return (WEATHER_ORDER.index(label), label)
    except ValueError:
        return (len(WEATHER_ORDER), label)


def _temperature_sort_key(label: str) -> tuple[int, str]:
    try:
        return (TEMPERATURE_ORDER.index(label), label)
    except ValueError:
        return (len(TEMPERATURE_ORDER), label)


def _mood_quadrant(valence: float, energy: float) -> str:
    if valence >= 0.5 and energy >= 0.5:
        return "Happy / Hype"
    if valence >= 0.5 and energy < 0.5:
        return "Calm / Chill"
    if valence < 0.5 and energy < 0.5:
        return "Sad / Reflective"
    return "Intense / Dark"


def _change_word(delta: float, positive: str, negative: str) -> str:
    if abs(delta) < 0.025:
        return "about the same"
    return positive if delta > 0 else negative


def _percent_change(delta: float, baseline: float | None) -> float:
    if baseline is None or baseline == 0:
        return 0
    return delta / baseline


def _listening_minutes(value: Any) -> float:
    return round(float(value or 0) / 60000, 1)


def _weather_shift_insight(
    weather: str,
    valence_delta: float,
    energy_delta: float,
    dominant_mood: str,
    top_artist: str | None,
) -> str:
    valence_text = _change_word(valence_delta, "brighter", "darker")
    energy_text = _change_word(energy_delta, "more energetic", "calmer")
    artist_text = f", especially {top_artist}" if top_artist else ""
    if valence_text == "about the same" and energy_text == "about the same":
        return f"When {weather.lower()} hits, your music stays close to your usual {dominant_mood} balance{artist_text}."
    return (
        f"When {weather.lower()} hits, your music becomes {valence_text} and "
        f"{energy_text}, leaning {dominant_mood}{artist_text}."
    )


def _top_tags_by_group(
    connection: Connection,
    group_column: str,
    start_date: object | None,
    weather_city: str,
    user_id: str,
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
          and tags.user_id = :user_id
        {date_filter}
        group by dw.{group_column}, tags.tag
        order by dw.{group_column}, listen_count desc, tags.tag asc
        """
    )
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in connection.execute(
        sql,
        {**_params(start_date, user_id), "weather_city": weather_city},
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
    def __init__(self, connection: Connection, user_id: str):
        self.connection = connection
        self.user_id = user_id

    def get_weather_correlation(self, period: str) -> WeatherCorrelationResponse:
        period_filter = build_period_filter(period)
        start_date = period_filter.start_date
        weather_city = get_weather_city(self.connection, user_id=self.user_id)
        daily_data = self._daily_data(start_date, weather_city)
        return WeatherCorrelationResponse(
            period=period_filter.period,
            weather_city=weather_city,
            daily_data=daily_data,
            summary_by_weather=self._summary("weather_category", start_date, weather_city),
            summary_by_temperature=self._summary("temperature_bucket", start_date, weather_city),
            summary_by_season=self._summary("season", start_date, weather_city),
            artist_weather_contexts=self._artist_weather_contexts(start_date, weather_city),
            **self._weather_mood_insights(start_date, weather_city),
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
              and m.user_id = :user_id
            {date_filter}
            order by d.date_id asc
            """
        )

        rows: list[dict[str, Any]] = []
        for row in self.connection.execute(
            sql,
            {**_params(start_date, self.user_id), "weather_city": weather_city},
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
        top_tags = _top_tags_by_group(
            self.connection,
            group_column,
            start_date,
            weather_city,
            self.user_id,
        )
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
              and m.user_id = :user_id
            {date_filter}
            group by dw.{group_column}
            order by total_listens desc, label asc
            """
        )

        summaries: list[dict[str, Any]] = []
        for row in self.connection.execute(
            sql,
            {**_params(start_date, self.user_id), "weather_city": weather_city},
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

    def _artist_weather_contexts(
        self,
        start_date: object | None,
        weather_city: str,
    ) -> list[dict[str, Any]]:
        date_filter = "and fl.date_id >= :start_date" if start_date is not None else ""
        sql = text(
            f"""
            with artist_weather as (
                select
                    fl.artist_id,
                    coalesce(da.name, 'Unknown Artist') as name,
                    da.image_url,
                    dw.weather_category,
                    count(*) as total_listens
                from {qualified_table("fact_listens")} fl
                join {qualified_table("dim_weather")} dw on fl.date_id = dw.date_id
                left join {qualified_table("dim_artists")} da
                    on fl.artist_id = da.artist_id and da.is_current = true
                where dw.city = :weather_city
                and fl.user_id = :user_id
                {date_filter}
                group by fl.artist_id, da.name, da.image_url, dw.weather_category
            ),
            ranked as (
                select
                    artist_id,
                    name,
                    image_url,
                    weather_category,
                    total_listens,
                    sum(total_listens) over (partition by artist_id) as artist_total_listens,
                    row_number() over (
                        partition by artist_id
                        order by total_listens desc, weather_category asc
                    ) as weather_rank
                from artist_weather
            )
            select
                artist_id,
                name,
                image_url,
                weather_category,
                total_listens,
                artist_total_listens
            from ranked
            where weather_rank = 1
              and weather_category not in ('Unknown')
            order by total_listens desc, name asc
            limit 8
            """
        )
        contexts: list[dict[str, Any]] = []
        for row in self.connection.execute(
            sql,
            {**_params(start_date, self.user_id), "weather_city": weather_city},
        ):
            item = row._mapping
            total_listens = int(item["total_listens"] or 0)
            artist_total = int(item["artist_total_listens"] or 0)
            share = total_listens / artist_total if artist_total else 0
            contexts.append(
                {
                    "artist_id": item["artist_id"],
                    "name": item["name"],
                    "image_url": item["image_url"],
                    "weather_category": item["weather_category"],
                    "total_listens": total_listens,
                    "weather_share": share,
                    "insight": (
                        f"{item['name']} shows up most on {item['weather_category'].lower()} "
                        f"days, with {total_listens:,} listens in this period."
                    ),
                }
            )
        return contexts

    def _weather_mood_insights(
        self,
        start_date: object | None,
        weather_city: str,
    ) -> dict[str, Any]:
        date_filter = "and fl.date_id >= :start_date" if start_date is not None else ""
        params = {**_params(start_date, self.user_id), "weather_city": weather_city}

        baseline = self._mood_baseline(date_filter, params)
        weather_rows = self._weather_mood_rows(date_filter, params)
        top_artists = self._top_weather_artists(date_filter, params)
        heatmap = self._weather_mood_heatmap(date_filter, params)
        temperature_trends = self._temperature_mood_trends(date_filter, params)

        weather_shifts = self._weather_mood_shifts(baseline, weather_rows, top_artists)
        weather_points = self._weather_mood_points(baseline, weather_rows, top_artists)

        weather_callout = None
        strongest_shift = next(
            (shift for shift in weather_shifts if shift["is_strongest_shift"]),
            None,
        )
        if strongest_shift is not None:
            direction = (
                "higher-energy"
                if abs(strongest_shift["energy_delta"]) >= abs(strongest_shift["valence_delta"])
                and strongest_shift["energy_delta"] > 0
                else "lower-energy"
                if abs(strongest_shift["energy_delta"]) >= abs(strongest_shift["valence_delta"])
                else "brighter"
                if strongest_shift["valence_delta"] > 0
                else "darker"
            )
            weather_callout = (
                f"{strongest_shift['weather_category']} is your strongest weather mood shift, "
                f"pulling your listening {direction}."
            )

        temperature_callout = self._temperature_mood_callout(temperature_trends)

        return {
            "mood_baseline": baseline,
            "weather_mood_shifts": weather_shifts,
            "weather_mood_heatmap": heatmap,
            "weather_mood_points": weather_points,
            "temperature_mood_trends": temperature_trends,
            "weather_mood_callout": weather_callout,
            "temperature_mood_callout": temperature_callout,
        }

    def _mood_baseline(self, date_filter: str, params: dict[str, object]) -> dict[str, Any]:
        sql = text(
            f"""
            select
                avg(dt.valence) as avg_valence,
                avg(dt.energy) as avg_energy,
                count(*) as total_listens,
                coalesce(sum({EFFECTIVE_MS_PLAYED_SQL}), 0) as total_ms_played
            from {qualified_table("fact_listens")} fl
            join {qualified_table("dim_weather")} dw on fl.date_id = dw.date_id
            join {qualified_table("dim_tracks")} dt on fl.track_id = dt.track_id
            where dw.city = :weather_city
              and fl.user_id = :user_id
              and dt.valence is not null
              and dt.energy is not null
              and dw.weather_category <> 'Unknown'
              {date_filter}
            """
        )
        item = self.connection.execute(sql, params).one()._mapping
        return {
            "avg_valence": _float_or_none(item["avg_valence"]),
            "avg_energy": _float_or_none(item["avg_energy"]),
            "total_listens": int(item["total_listens"] or 0),
            "listening_minutes": _listening_minutes(item["total_ms_played"]),
        }

    def _weather_mood_rows(
        self,
        date_filter: str,
        params: dict[str, object],
    ) -> list[dict[str, Any]]:
        sql = text(
            f"""
            select
                dw.weather_category,
                avg(dt.valence) as avg_valence,
                avg(dt.energy) as avg_energy,
                count(*) as stream_count,
                coalesce(sum({EFFECTIVE_MS_PLAYED_SQL}), 0) as total_ms_played
            from {qualified_table("fact_listens")} fl
            join {qualified_table("dim_weather")} dw on fl.date_id = dw.date_id
            join {qualified_table("dim_tracks")} dt on fl.track_id = dt.track_id
            where dw.city = :weather_city
              and fl.user_id = :user_id
              and dt.valence is not null
              and dt.energy is not null
              and dw.weather_category <> 'Unknown'
              {date_filter}
            group by dw.weather_category
            order by stream_count desc, dw.weather_category asc
            """
        )
        rows: list[dict[str, Any]] = []
        for row in self.connection.execute(sql, params):
            item = row._mapping
            avg_valence = float(item["avg_valence"])
            avg_energy = float(item["avg_energy"])
            rows.append(
                {
                    "weather_category": str(item["weather_category"]),
                    "avg_valence": avg_valence,
                    "avg_energy": avg_energy,
                    "stream_count": int(item["stream_count"] or 0),
                    "listening_minutes": _listening_minutes(item["total_ms_played"]),
                    "dominant_mood_quadrant": _mood_quadrant(avg_valence, avg_energy),
                }
            )
        return sorted(rows, key=lambda row: _weather_sort_key(row["weather_category"]))

    def _top_weather_artists(
        self,
        date_filter: str,
        params: dict[str, object],
    ) -> dict[str, str]:
        sql = text(
            f"""
            with artist_weather as (
                select
                    dw.weather_category,
                    coalesce(da.name, dt.artist_name, 'Unknown Artist') as artist_name,
                    count(*) as stream_count
                from {qualified_table("fact_listens")} fl
                join {qualified_table("dim_weather")} dw on fl.date_id = dw.date_id
                join {qualified_table("dim_tracks")} dt on fl.track_id = dt.track_id
                left join {qualified_table("dim_artists")} da
                    on fl.artist_id = da.artist_id and da.is_current = true
                where dw.city = :weather_city
                  and fl.user_id = :user_id
                  and dt.valence is not null
                  and dt.energy is not null
                  and dw.weather_category <> 'Unknown'
                  {date_filter}
                group by dw.weather_category, da.name, dt.artist_name
            ),
            ranked as (
                select
                    weather_category,
                    artist_name,
                    row_number() over (
                        partition by weather_category
                        order by stream_count desc, artist_name asc
                    ) as artist_rank
                from artist_weather
            )
            select weather_category, artist_name
            from ranked
            where artist_rank = 1
            """
        )
        return {
            str(row._mapping["weather_category"]): str(row._mapping["artist_name"])
            for row in self.connection.execute(sql, params)
        }

    def _weather_mood_shifts(
        self,
        baseline: dict[str, Any],
        weather_rows: list[dict[str, Any]],
        top_artists: dict[str, str],
    ) -> list[dict[str, Any]]:
        baseline_valence = baseline["avg_valence"]
        baseline_energy = baseline["avg_energy"]
        shifts: list[dict[str, Any]] = []
        if baseline_valence is None or baseline_energy is None:
            return shifts

        strongest_weather = None
        strongest_distance = -1.0
        for row in weather_rows:
            valence_delta = row["avg_valence"] - baseline_valence
            energy_delta = row["avg_energy"] - baseline_energy
            distance = (valence_delta**2 + energy_delta**2) ** 0.5
            if distance > strongest_distance:
                strongest_weather = row["weather_category"]
                strongest_distance = distance
            shifts.append(
                {
                    "weather_category": row["weather_category"],
                    "total_listens": row["stream_count"],
                    "listening_minutes": row["listening_minutes"],
                    "avg_valence": row["avg_valence"],
                    "avg_energy": row["avg_energy"],
                    "valence_delta": valence_delta,
                    "energy_delta": energy_delta,
                    "valence_percent_change": _percent_change(valence_delta, baseline_valence),
                    "energy_percent_change": _percent_change(energy_delta, baseline_energy),
                    "dominant_mood_quadrant": row["dominant_mood_quadrant"],
                    "top_artist_name": top_artists.get(row["weather_category"]),
                    "insight": _weather_shift_insight(
                        row["weather_category"],
                        valence_delta,
                        energy_delta,
                        row["dominant_mood_quadrant"],
                        top_artists.get(row["weather_category"]),
                    ),
                    "is_strongest_shift": False,
                }
            )

        for shift in shifts:
            shift["is_strongest_shift"] = shift["weather_category"] == strongest_weather
        return shifts

    def _weather_mood_heatmap(
        self,
        date_filter: str,
        params: dict[str, object],
    ) -> list[dict[str, Any]]:
        sql = text(
            f"""
            with mooded as (
                select
                    dw.weather_category,
                    {MOOD_QUADRANT_SQL} as mood_quadrant,
                    {EFFECTIVE_MS_PLAYED_SQL} as effective_ms_played
                from {qualified_table("fact_listens")} fl
                join {qualified_table("dim_weather")} dw on fl.date_id = dw.date_id
                join {qualified_table("dim_tracks")} dt on fl.track_id = dt.track_id
                where dw.city = :weather_city
                  and fl.user_id = :user_id
                  and dt.valence is not null
                  and dt.energy is not null
                  and dw.weather_category <> 'Unknown'
                  {date_filter}
            )
            select
                weather_category,
                mood_quadrant,
                count(*) as stream_count,
                coalesce(sum(effective_ms_played), 0) as total_ms_played
            from mooded
            group by weather_category, mood_quadrant
            """
        )
        grouped: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
        weather_totals: dict[str, int] = defaultdict(int)
        strongest_key: tuple[str, str] | None = None
        strongest_count = -1

        for row in self.connection.execute(sql, params):
            item = row._mapping
            weather = str(item["weather_category"])
            quadrant = str(item["mood_quadrant"])
            count = int(item["stream_count"] or 0)
            grouped[weather][quadrant] = {
                "stream_count": count,
                "listening_minutes": _listening_minutes(item["total_ms_played"]),
            }
            weather_totals[weather] += count
            if count > strongest_count:
                strongest_key = (weather, quadrant)
                strongest_count = count

        cells: list[dict[str, Any]] = []
        for weather in sorted(grouped.keys(), key=_weather_sort_key):
            for quadrant in MOOD_QUADRANTS:
                values = grouped[weather].get(
                    quadrant,
                    {"stream_count": 0, "listening_minutes": 0.0},
                )
                total = weather_totals[weather]
                cells.append(
                    {
                        "weather_category": weather,
                        "mood_quadrant": quadrant,
                        "stream_count": values["stream_count"],
                        "listening_minutes": values["listening_minutes"],
                        "percentage": values["stream_count"] / total if total else 0,
                        "is_strongest": strongest_key == (weather, quadrant),
                    }
                )
        return cells

    def _weather_mood_points(
        self,
        baseline: dict[str, Any],
        weather_rows: list[dict[str, Any]],
        top_artists: dict[str, str],
    ) -> list[dict[str, Any]]:
        baseline_valence = baseline["avg_valence"]
        baseline_energy = baseline["avg_energy"]
        if baseline_valence is None or baseline_energy is None:
            return []

        points: list[dict[str, Any]] = []
        most_distinct_weather = None
        highest_distance = -1.0
        for row in weather_rows:
            distance = (
                (row["avg_valence"] - baseline_valence) ** 2
                + (row["avg_energy"] - baseline_energy) ** 2
            ) ** 0.5
            if distance > highest_distance:
                highest_distance = distance
                most_distinct_weather = row["weather_category"]
            points.append(
                {
                    "weather_category": row["weather_category"],
                    "avg_valence": row["avg_valence"],
                    "avg_energy": row["avg_energy"],
                    "dominant_mood_quadrant": row["dominant_mood_quadrant"],
                    "top_artist_name": top_artists.get(row["weather_category"]),
                    "stream_count": row["stream_count"],
                    "listening_minutes": row["listening_minutes"],
                    "distance_from_overall": distance,
                    "is_most_distinct": False,
                }
            )

        for point in points:
            point["is_most_distinct"] = point["weather_category"] == most_distinct_weather
        return points

    def _temperature_mood_trends(
        self,
        date_filter: str,
        params: dict[str, object],
    ) -> list[dict[str, Any]]:
        sql = text(
            f"""
            select
                dw.temperature_bucket,
                avg(dt.valence) as avg_valence,
                avg(dt.energy) as avg_energy,
                count(*) as stream_count,
                coalesce(sum({EFFECTIVE_MS_PLAYED_SQL}), 0) as total_ms_played
            from {qualified_table("fact_listens")} fl
            join {qualified_table("dim_weather")} dw on fl.date_id = dw.date_id
            join {qualified_table("dim_tracks")} dt on fl.track_id = dt.track_id
            where dw.city = :weather_city
              and fl.user_id = :user_id
              and dt.valence is not null
              and dt.energy is not null
              and dw.temperature_bucket <> 'Unknown'
              {date_filter}
            group by dw.temperature_bucket
            """
        )
        trends: list[dict[str, Any]] = []
        for row in self.connection.execute(sql, params):
            item = row._mapping
            trends.append(
                {
                    "temperature_bucket": str(item["temperature_bucket"]),
                    "avg_valence": float(item["avg_valence"]),
                    "avg_energy": float(item["avg_energy"]),
                    "stream_count": int(item["stream_count"] or 0),
                    "listening_minutes": _listening_minutes(item["total_ms_played"]),
                    "is_highest_valence": False,
                    "is_highest_energy": False,
                }
            )

        if trends:
            max_valence = max(trends, key=lambda trend: trend["avg_valence"])
            max_energy = max(trends, key=lambda trend: trend["avg_energy"])
            for trend in trends:
                trend["is_highest_valence"] = trend is max_valence
                trend["is_highest_energy"] = trend is max_energy

        return sorted(trends, key=lambda trend: _temperature_sort_key(trend["temperature_bucket"]))

    def _temperature_mood_callout(self, trends: list[dict[str, Any]]) -> str | None:
        if not trends:
            return None
        hottest = next(
            (trend for trend in trends if trend["temperature_bucket"] == "Hot"),
            trends[-1],
        )
        coldest = next(
            (trend for trend in trends if trend["temperature_bucket"] == "Freezing"),
            trends[0],
        )
        valence_delta = hottest["avg_valence"] - coldest["avg_valence"]
        if abs(valence_delta) >= 0.04:
            direction = "happier" if valence_delta > 0 else "darker"
            return f"Your music gets {direction} as the temperature rises."
        highest_energy = max(trends, key=lambda trend: trend["avg_energy"])
        return (
            f"Your highest-energy listening happens in "
            f"{highest_energy['temperature_bucket'].lower()} weather."
        )


def validate_weather_period(period: str) -> None:
    if period not in VALID_PERIODS:
        raise ValueError("Invalid period. Accepted values: 7d, 30d, 6m, all")
