from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text

from app.core.alerts import send_slack_alert
from app.db import db_connection, qualified_table

VALID_MOODS = ("happy", "sad", "angry", "calm", "energetic", "melancholic")


@dataclass(frozen=True)
class QualityResult:
    suite: str
    expectation: str
    passed: bool
    observed_value: Any


class QualityGateFailure(RuntimeError):
    def __init__(self, failures: list[QualityResult]):
        self.failures = failures
        details = "; ".join(
            f"{item.suite}.{item.expectation} observed={item.observed_value!r}"
            for item in failures
        )
        super().__init__(f"Data quality gate failed: {details}")


def _result(suite: str, expectation: str, passed: bool, observed_value: Any) -> QualityResult:
    return QualityResult(
        suite=suite,
        expectation=expectation,
        passed=passed,
        observed_value=observed_value,
    )


def run_raw_recent_tracks_suite() -> list[QualityResult]:
    results: list[QualityResult] = []
    with db_connection() as connection:
        null_count = connection.execute(
            text(
                """
                select count(*) as value
                from raw.recent_tracks
                where user_id is null
                   or track_name is null
                   or artist_name is null
                   or played_at is null
                """
            )
        ).scalar_one()
        results.append(
            _result("raw_recent_tracks", "required_columns_not_null", null_count == 0, null_count)
        )

        future_count = connection.execute(
            text(
                """
                select count(*) as value
                from raw.recent_tracks
                where played_at >= current_timestamp
                """
            )
        ).scalar_one()
        results.append(
            _result("raw_recent_tracks", "played_at_not_future", future_count == 0, future_count)
        )

        row_count = connection.execute(text("select count(*) from raw.recent_tracks")).scalar_one()
        results.append(_result("raw_recent_tracks", "row_count_minimum", row_count >= 1, row_count))
    return results


def run_dim_tracks_mood_suite() -> list[QualityResult]:
    threshold = float(os.getenv("MOOD_NULL_RATE_THRESHOLD", "0.75"))
    valid_moods = ",".join(f"'{mood}'" for mood in VALID_MOODS)
    results: list[QualityResult] = []

    with db_connection() as connection:
        confidence_outliers = connection.execute(
            text(
                f"""
                select count(*) as value
                from {qualified_table("dim_tracks")}
                where mood_confidence is not null
                  and (mood_confidence < 0 or mood_confidence > 1)
                """
            )
        ).scalar_one()
        results.append(
            _result(
                "dim_tracks_mood",
                "mood_confidence_between_0_and_1",
                confidence_outliers == 0,
                confidence_outliers,
            )
        )

        invalid_labels = connection.execute(
            text(
                f"""
                select count(*) as value
                from {qualified_table("dim_tracks")}
                where mood_label is not null and mood_label not in ({valid_moods})
                """
            )
        ).scalar_one()
        results.append(
            _result("dim_tracks_mood", "mood_label_in_valid_set", invalid_labels == 0, invalid_labels)
        )

        null_rate = connection.execute(
            text(
                f"""
                select
                    case
                        when count(*) = 0 then 0
                        else cast(sum(case when mood_label is null then 1 else 0 end) as numeric) / count(*)
                    end as value
                from {qualified_table("dim_tracks")}
                """
            )
        ).scalar_one()
        results.append(
            _result("dim_tracks_mood", "mood_label_null_rate", null_rate <= threshold, null_rate)
        )

    return results


def run_raw_weather_suite() -> list[QualityResult]:
    results: list[QualityResult] = []
    with db_connection() as connection:
        null_count = connection.execute(
            text(
                """
                select count(*) as value
                from raw.weather
                where date is null or temp_c is null or weather_code is null
                """
            )
        ).scalar_one()
        results.append(_result("raw_weather", "required_columns_not_null", null_count == 0, null_count))

        out_of_range = connection.execute(
            text(
                """
                select count(*) as value
                from raw.weather
                where temp_c < -60 or temp_c > 60
                """
            )
        ).scalar_one()
        results.append(_result("raw_weather", "temp_c_sanity_range", out_of_range == 0, out_of_range))
    return results


def run_quality_gate() -> dict[str, Any]:
    results = [
        *run_raw_recent_tracks_suite(),
        *run_dim_tracks_mood_suite(),
        *run_raw_weather_suite(),
    ]
    failures = [result for result in results if not result.passed]

    if failures:
        send_slack_alert(
            "data_quality",
            "Quality gate failed: "
            + ", ".join(f"{item.suite}.{item.expectation}" for item in failures),
            failed_records=len(failures),
        )
        raise QualityGateFailure(failures)

    return {
        "passed": True,
        "expectations": len(results),
        "suites": sorted({result.suite for result in results}),
    }
