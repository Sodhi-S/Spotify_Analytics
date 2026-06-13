from __future__ import annotations

import pickle
import tempfile
import time
from pathlib import Path
from typing import Any

import requests
from sqlalchemy import text

from app.core.alerts import send_slack_alert
from app.core.config import get_settings
from app.db import db_connection, qualified_table
from app.ingestion.itunes import ITunesClient
from app.ingestion.loader import RawLoader


def find_unclassified_tracks(limit: int = 250) -> dict[str, int]:
    with db_connection() as connection:
        pending_preview = connection.execute(
            text(
                f"""
                select count(*) as count_value
                from {qualified_table("dim_tracks")}
                where mood_label is null and preview_url is null
                """
            )
        ).scalar_one()
        pending_inference = connection.execute(
            text(
                f"""
                select count(*) as count_value
                from {qualified_table("dim_tracks")}
                where mood_label is null and preview_url is not null
                """
            )
        ).scalar_one()
    return {
        "pending_preview_lookup": min(int(pending_preview or 0), limit),
        "pending_inference": min(int(pending_inference or 0), limit),
    }


def fetch_itunes_previews(limit: int = 100) -> dict[str, int]:
    client = ITunesClient()
    found = 0
    inspected = 0

    with db_connection() as connection:
        rows = connection.execute(
            text(
                f"""
                select track_id, name, artist_name
                from {qualified_table("dim_tracks")}
                where mood_label is null and preview_url is null
                order by artist_name, name
                limit :limit
                """
            ),
            {"limit": limit},
        ).fetchall()

        for row in rows:
            inspected += 1
            track = row._mapping
            try:
                preview_url = client.get_preview_url(track["artist_name"], track["name"])
                if preview_url:
                    connection.execute(
                        text(
                            f"""
                            update {qualified_table("dim_tracks")}
                            set preview_url = :preview_url
                            where track_id = :track_id
                            """
                        ),
                        {"preview_url": preview_url, "track_id": track["track_id"]},
                    )
                    found += 1
            except Exception as exc:  # noqa: BLE001
                RawLoader(connection).insert_failed("itunes_preview", dict(track), str(exc))

    return {"inspected": inspected, "found": found}


def download_preview(preview_url: str) -> Path:
    response = requests.get(preview_url, timeout=30)
    response.raise_for_status()
    suffix = Path(preview_url.split("?")[0]).suffix or ".m4a"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    with tmp:
        tmp.write(response.content)
    return Path(tmp.name)


def extract_features(y: Any, sr: int) -> Any:
    import librosa
    import numpy as np

    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=20)
    chroma = librosa.feature.chroma_stft(y=y, sr=sr)
    spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
    rms = librosa.feature.rms(y=y)

    features = [
        mfcc.mean(axis=1),
        mfcc.std(axis=1),
        chroma.mean(axis=1),
        chroma.std(axis=1),
        spectral_centroid.mean(axis=1),
        spectral_centroid.std(axis=1),
        rms.mean(axis=1),
        rms.std(axis=1),
    ]
    return np.concatenate(features)


def classify_mood(preview_path: Path) -> tuple[str, float, float]:
    import librosa

    settings = get_settings()
    started = time.perf_counter()
    with settings.mood_model_path.open("rb") as model_file:
        model = pickle.load(model_file)

    y, sr = librosa.load(preview_path, sr=settings.target_sample_rate)
    features = extract_features(y, sr)
    probabilities = model.predict_proba([features])[0]
    best_index = int(probabilities.argmax())
    mood_label = str(model.classes_[best_index])
    confidence = float(probabilities[best_index])
    elapsed_seconds = time.perf_counter() - started
    return mood_label, confidence, elapsed_seconds


def run_librosa_inference(limit: int = 50) -> dict[str, int | float]:
    processed = 0
    failed = 0
    total_seconds = 0.0

    with db_connection() as connection:
        rows = connection.execute(
            text(
                f"""
                select track_id, name, artist_name, preview_url
                from {qualified_table("dim_tracks")}
                where mood_label is null and preview_url is not null
                order by artist_name, name
                limit :limit
                """
            ),
            {"limit": limit},
        ).fetchall()

        for row in rows:
            track = dict(row._mapping)
            preview_path: Path | None = None
            try:
                preview_path = download_preview(track["preview_url"])
                mood_label, confidence, elapsed = classify_mood(preview_path)
                total_seconds += elapsed
                connection.execute(
                    text(
                        """
                        insert into raw.mood_classification_results (
                            track_id, mood_label, mood_confidence,
                            inference_seconds, classified_at
                        )
                        values (
                            :track_id, :mood_label, :mood_confidence,
                            :inference_seconds, current_timestamp
                        )
                        """
                    ),
                    {
                        "track_id": track["track_id"],
                        "mood_label": mood_label,
                        "mood_confidence": confidence,
                        "inference_seconds": elapsed,
                    },
                )
                processed += 1
            except Exception as exc:  # noqa: BLE001
                failed += 1
                RawLoader(connection).insert_failed("mood_classification", track, str(exc))
            finally:
                if preview_path is not None:
                    preview_path.unlink(missing_ok=True)

    if failed:
        send_slack_alert("mood_classification", "Track-level inference failures", failed)

    return {
        "processed": processed,
        "failed": failed,
        "avg_inference_seconds": total_seconds / processed if processed else 0.0,
    }


def write_mood_labels() -> dict[str, int]:
    with db_connection() as connection:
        result = connection.execute(
            text(
                f"""
                with latest as (
                    select distinct on (track_id)
                        id,
                        track_id,
                        mood_label,
                        mood_confidence
                    from raw.mood_classification_results
                    where applied_at is null
                    order by track_id, classified_at desc
                ),
                updated as (
                    update {qualified_table("dim_tracks")} dt
                    set
                        mood_label = latest.mood_label,
                        mood_confidence = latest.mood_confidence
                    from latest
                    where dt.track_id = latest.track_id
                    returning latest.id
                )
                update raw.mood_classification_results results
                set applied_at = current_timestamp
                from updated
                where results.id = updated.id
                """
            )
        )
    return {"updated": result.rowcount if result.rowcount is not None else 0}
