from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.api.schemas import ArtistMoodFingerprintsResponse
from app.db import qualified_table
from app.services.overview import VALID_PERIODS, build_period_filter

MOOD_FEATURES: dict[str, tuple[float, float]] = {
    "happy": (0.9, 0.65),
    "energetic": (0.78, 0.9),
    "calm": (0.68, 0.25),
    "melancholic": (0.35, 0.3),
    "sad": (0.2, 0.28),
    "angry": (0.18, 0.85),
}

TAG_FEATURES: tuple[tuple[tuple[str, ...], tuple[float, float]], ...] = (
    (("sad", "melancholy", "melancholic", "emo", "heartbreak"), (0.22, 0.32)),
    (("ambient", "chill", "acoustic", "folk", "sleep"), (0.62, 0.28)),
    (("dance", "house", "edm", "disco", "funk", "club"), (0.82, 0.86)),
    (("trap", "rap", "hip hop", "hip-hop"), (0.56, 0.76)),
    (("metal", "punk", "hardcore", "rock"), (0.42, 0.82)),
    (("rnb", "r&b", "soul", "jazz"), (0.58, 0.46)),
    (("pop", "k-pop", "dance-pop"), (0.72, 0.66)),
    (("indie", "alternative"), (0.55, 0.52)),
)


@dataclass
class ArtistAccumulator:
    artist_id: str
    name: str
    image_url: str | None = None
    play_count: int = 0
    total_ms_played: int = 0
    weighted_valence: float = 0
    weighted_energy: float = 0
    scored_plays: int = 0
    late_night_plays: int = 0
    evening_plays: int = 0


def _params(start_date: object | None) -> dict[str, object]:
    return {} if start_date is None else {"start_date": start_date}


def _date_clause(start_date: object | None) -> str:
    return "" if start_date is None else "where fl.date_id >= :start_date"


def _split_tags(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item).strip().lower() for item in value if str(item).strip()]
    return [tag.strip().lower() for tag in str(value).split(",") if tag.strip()]


def _feature_from_tags(tags: list[str]) -> tuple[float, float] | None:
    if not tags:
        return None
    tag_text = " ".join(tags)
    matches = [
        feature
        for needles, feature in TAG_FEATURES
        if any(needle in tag_text for needle in needles)
    ]
    if not matches:
        return None
    return (
        sum(match[0] for match in matches) / len(matches),
        sum(match[1] for match in matches) / len(matches),
    )


def _track_features(mood_label: str | None, tags: list[str]) -> tuple[float, float] | None:
    if mood_label in MOOD_FEATURES:
        return MOOD_FEATURES[mood_label]
    return _feature_from_tags(tags)


def _mood_label(valence: float | None, energy: float | None, late_night_share: float) -> str:
    if valence is None or energy is None:
        return "Pending Mood Data"
    if late_night_share >= 0.45:
        return "Night Artist"
    if energy >= 0.65 and valence >= 0.6:
        return "Hype Artist"
    if energy >= 0.65 and valence < 0.4:
        return "Rage Artist"
    if energy < 0.45 and valence < 0.45:
        return "Sad Artist"
    if energy < 0.5 and valence >= 0.45:
        return "Comfort Artist"
    if energy >= 0.55:
        return "Momentum Artist"
    return "Reflective Artist"


def _dominant_context(late_night_share: float, evening_share: float) -> str:
    if late_night_share >= 0.45:
        return "Late night"
    if evening_share >= 0.45:
        return "Evening"
    return "All-day rotation"


def _insight(name: str, label: str, valence: float | None, energy: float | None, context: str) -> str:
    if valence is None or energy is None:
        return (
            f"{name} is prominent in your listening history, but needs more mood-classified "
            "tracks before a precise fingerprint is available."
        )
    valence_text = "brighter" if valence >= 0.6 else "darker" if valence < 0.4 else "balanced"
    energy_text = "high-energy" if energy >= 0.65 else "low-energy" if energy < 0.45 else "medium-energy"
    return (
        f"{name} reads as a {label}: {valence_text}, {energy_text}, "
        f"and most associated with {context.lower()} listening."
    )


def _callout(
    kind: str,
    artist: dict[str, Any] | None,
    metric: str,
    fallback: str,
) -> dict[str, Any]:
    if artist is None or artist.get(metric) is None:
        return {"kind": kind, "artist_name": None, "value": None, "text": fallback}
    value = float(artist[metric])
    return {
        "kind": kind,
        "artist_name": artist["name"],
        "value": value,
        "text": f"Your {kind.replace('_', ' ')} is {artist['name']} at {value:.2f}.",
    }


class ArtistMoodFingerprintService:
    def __init__(self, connection: Connection):
        self.connection = connection

    def get_artist_mood_fingerprints(
        self,
        period: str,
        limit: int = 10,
    ) -> ArtistMoodFingerprintsResponse:
        period_filter = build_period_filter(period)
        rows = self.connection.execute(
            text(
                f"""
                select
                    fl.artist_id,
                    coalesce(da.name, dt.artist_name, 'Unknown Artist') as artist_name,
                    da.image_url,
                    da.genres as artist_genres,
                    dt.valence,
                    dt.energy,
                    dt.mood_label,
                    dt.top_tags,
                    count(*) as play_count,
                    coalesce(sum(fl.ms_played), 0) as total_ms_played,
                    sum(case when fl.hour >= 22 or fl.hour < 5 then 1 else 0 end) as late_night_plays,
                    sum(case when fl.hour >= 17 and fl.hour < 22 then 1 else 0 end) as evening_plays
                from {qualified_table("fact_listens")} fl
                left join {qualified_table("dim_tracks")} dt on fl.track_id = dt.track_id
                left join {qualified_table("dim_artists")} da
                    on fl.artist_id = da.artist_id and da.is_current = true
                {_date_clause(period_filter.start_date)}
                group by
                    fl.artist_id,
                    da.name,
                    dt.artist_name,
                    da.image_url,
                    da.genres,
                    dt.valence,
                    dt.energy,
                    dt.mood_label,
                    dt.top_tags
                order by count(*) desc
                """
            ),
            _params(period_filter.start_date),
        )

        artists: dict[str, ArtistAccumulator] = {}
        for row in rows:
            item = row._mapping
            artist_id = item["artist_id"]
            if artist_id not in artists:
                artists[artist_id] = ArtistAccumulator(
                    artist_id=artist_id,
                    name=item["artist_name"],
                    image_url=item["image_url"],
                )
            artist = artists[artist_id]
            play_count = int(item["play_count"] or 0)
            artist.play_count += play_count
            artist.total_ms_played += int(item["total_ms_played"] or 0)
            artist.late_night_plays += int(item["late_night_plays"] or 0)
            artist.evening_plays += int(item["evening_plays"] or 0)

            if item["valence"] is not None and item["energy"] is not None:
                features = (float(item["valence"]), float(item["energy"]))
            else:
                tags = [*_split_tags(item["top_tags"]), *_split_tags(item["artist_genres"])]
                features = _track_features(item["mood_label"], tags)
            if features is not None:
                artist.weighted_valence += features[0] * play_count
                artist.weighted_energy += features[1] * play_count
                artist.scored_plays += play_count

        ranked = sorted(artists.values(), key=lambda artist: (-artist.play_count, artist.name))[:limit]
        response_artists: list[dict[str, Any]] = []
        for index, artist in enumerate(ranked, start=1):
            avg_valence = (
                artist.weighted_valence / artist.scored_plays if artist.scored_plays else None
            )
            avg_energy = artist.weighted_energy / artist.scored_plays if artist.scored_plays else None
            late_share = artist.late_night_plays / artist.play_count if artist.play_count else 0
            evening_share = artist.evening_plays / artist.play_count if artist.play_count else 0
            dominant_context = _dominant_context(late_share, evening_share)
            label = _mood_label(avg_valence, avg_energy, late_share)
            response_artists.append(
                {
                    "rank": index,
                    "artist_id": artist.artist_id,
                    "name": artist.name,
                    "image_url": artist.image_url,
                    "mood_label": label,
                    "avg_valence": avg_valence,
                    "avg_energy": avg_energy,
                    "play_count": artist.play_count,
                    "listening_minutes": round(artist.total_ms_played / 60000, 1),
                    "dominant_context": dominant_context,
                    "insight": _insight(
                        artist.name,
                        label,
                        avg_valence,
                        avg_energy,
                        dominant_context,
                    ),
                }
            )

        scored = [artist for artist in response_artists if artist["avg_valence"] is not None]
        callouts = [
            _callout(
                "happiest_artist",
                max(scored, key=lambda artist: artist["avg_valence"], default=None),
                "avg_valence",
                "Mood scores are pending until more classified tracks are available.",
            ),
            _callout(
                "saddest_artist",
                min(scored, key=lambda artist: artist["avg_valence"], default=None),
                "avg_valence",
                "Mood scores are pending until more classified tracks are available.",
            ),
            _callout(
                "highest_energy_artist",
                max(scored, key=lambda artist: artist["avg_energy"], default=None),
                "avg_energy",
                "Energy scores are pending until more classified tracks are available.",
            ),
            _callout(
                "calmest_artist",
                min(scored, key=lambda artist: artist["avg_energy"], default=None),
                "avg_energy",
                "Energy scores are pending until more classified tracks are available.",
            ),
        ]

        return ArtistMoodFingerprintsResponse(
            period=period_filter.period,
            artists=response_artists,
            callouts=callouts,
        )


def validate_artist_mood_params(period: str, limit: int) -> None:
    if period not in VALID_PERIODS:
        raise ValueError("Invalid period. Accepted values: 7d, 30d, 6m, all")
    if limit < 5 or limit > 10:
        raise ValueError("Limit must be between 5 and 10")
