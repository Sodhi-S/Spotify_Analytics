from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import requests
from sqlalchemy import text

from app.core.alerts import send_slack_alert
from app.core.config import ROOT_DIR, get_settings
from app.db import db_connection, qualified_table
from app.ingestion.itunes import ITunesClient
from app.ingestion.loader import RawLoader

MODEL_NAME = "amaai-lab/music2emo"
MODEL_VERSION = "music2emo-v1.0"


def _normalise_scale_1_to_9(value: float | None) -> float | None:
    if value is None:
        return None
    return max(0.0, min(1.0, (float(value) - 1.0) / 8.0))


def _mood_from_valence_energy(valence: float | None, energy: float | None) -> str | None:
    if valence is None or energy is None:
        return None
    if energy >= 0.65 and valence >= 0.55:
        return "energetic"
    if valence >= 0.65:
        return "happy"
    if energy < 0.45 and valence >= 0.45:
        return "calm"
    if energy >= 0.65 and valence < 0.45:
        return "angry"
    if valence < 0.35:
        return "sad"
    return "melancholic"


def find_unscored_music2emo_tracks(limit: int = 250) -> dict[str, int]:
    with db_connection() as connection:
        pending_preview = connection.execute(
            text(
                f"""
                select count(*) as count_value
                from {qualified_table("dim_tracks")} tracks
                left join raw.track_emotion_features features
                    on tracks.track_id = features.track_id
                where features.track_id is null
                  and tracks.preview_url is null
                """
            )
        ).scalar_one()
        pending_inference = connection.execute(
            text(
                f"""
                select count(*) as count_value
                from {qualified_table("dim_tracks")} tracks
                left join raw.track_emotion_features features
                    on tracks.track_id = features.track_id
                where tracks.preview_url is not null
                  and (
                    features.track_id is null
                    or features.error_message is not null
                  )
                """
            )
        ).scalar_one()
    return {
        "pending_preview_lookup": min(int(pending_preview or 0), limit),
        "pending_inference": min(int(pending_inference or 0), limit),
    }


def run_music2emo_pipeline(
    preview_limit: int | None = None,
    inference_limit: int | None = None,
    rebuild_models: bool = True,
    refresh_before_lookup: bool = True,
) -> dict[str, Any]:
    settings = get_settings()
    effective_preview_limit = preview_limit if preview_limit is not None else settings.music2emo_preview_limit
    effective_inference_limit = (
        inference_limit if inference_limit is not None else settings.music2emo_inference_limit
    )

    result: dict[str, Any] = {}
    if refresh_before_lookup:
        result["dbt_before"] = rebuild_music2emo_models()

    result["pending_before"] = find_unscored_music2emo_tracks(
        limit=max(effective_preview_limit, effective_inference_limit)
    )
    result["preview_lookup"] = fetch_music2emo_previews(limit=effective_preview_limit)
    result["inference"] = run_music2emo_inference(limit=effective_inference_limit)
    if rebuild_models:
        result["dbt_after"] = rebuild_music2emo_models()
    result["pending_after"] = find_unscored_music2emo_tracks(
        limit=max(effective_preview_limit, effective_inference_limit)
    )
    return result


def rebuild_music2emo_models() -> dict[str, object]:
    dbt_executable = _dbt_executable()
    command = [
        dbt_executable,
        "run",
        "--profiles-dir",
        ".",
        "--select",
        "dim_tracks",
        "mart_listening_summary",
    ]
    result = subprocess.run(
        command,
        cwd=ROOT_DIR / "dbt",
        check=True,
        capture_output=True,
        text=True,
    )
    return {
        "command": " ".join(command),
        "returncode": result.returncode,
    }


def _dbt_executable() -> str:
    configured = get_settings().dbt_executable
    if shutil.which(configured):
        return configured

    local_conda_dbt = "/opt/anaconda3/envs/ve/bin/dbt"
    if shutil.which(local_conda_dbt):
        return local_conda_dbt

    return configured


def fetch_music2emo_previews(limit: int = 100) -> dict[str, int]:
    client = ITunesClient()
    found = 0
    inspected = 0

    with db_connection() as connection:
        rows = connection.execute(
            text(
                f"""
                select tracks.track_id, tracks.name, tracks.artist_name
                from {qualified_table("dim_tracks")} tracks
                left join raw.track_emotion_features features
                    on tracks.track_id = features.track_id
                where tracks.preview_url is null
                  and (
                    features.track_id is null
                    or features.error_message = 'No iTunes preview found.'
                  )
                order by tracks.artist_name, tracks.name
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
                else:
                    connection.execute(
                        text(
                            """
                            insert into raw.track_emotion_features (
                                track_id, predicted_moods, model_name, model_version,
                                source_audio_url, classified_at, error_message
                            )
                            values (
                                :track_id, '[]'::jsonb, :model_name, :model_version,
                                null, current_timestamp, :error_message
                            )
                            on conflict (track_id) do update set
                                model_name = excluded.model_name,
                                model_version = excluded.model_version,
                                source_audio_url = excluded.source_audio_url,
                                classified_at = current_timestamp,
                                error_message = excluded.error_message
                            """
                        ),
                        {
                            "track_id": track["track_id"],
                            "model_name": MODEL_NAME,
                            "model_version": MODEL_VERSION,
                            "error_message": "No iTunes preview found.",
                        },
                    )
            except Exception as exc:  # noqa: BLE001
                RawLoader(connection).insert_failed("music2emo_preview", dict(track), str(exc))

    return {"inspected": inspected, "found": found}


def download_preview(preview_url: str) -> Path:
    response = requests.get(preview_url, timeout=30)
    response.raise_for_status()
    suffix = Path(preview_url.split("?")[0]).suffix or ".m4a"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    with tmp:
        tmp.write(response.content)
    return Path(tmp.name)


def convert_preview_to_wav(preview_path: Path) -> Path:
    if preview_path.suffix.lower() == ".wav":
        return preview_path

    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        conda_env_ffmpeg = Path(sys.executable).resolve().parent / "ffmpeg"
        if conda_env_ffmpeg.exists():
            ffmpeg_path = str(conda_env_ffmpeg)
    if not ffmpeg_path:
        raise RuntimeError(
            "ffmpeg is required to convert iTunes AAC/M4A previews to WAV before Music2Emo "
            "inference. Install it in the worker env with: conda install ffmpeg -c conda-forge"
        )

    wav_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    wav_path = Path(wav_file.name)
    wav_file.close()
    command = [
        ffmpeg_path,
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(preview_path),
        "-ac",
        "1",
        "-ar",
        "24000",
        str(wav_path),
    ]
    subprocess.run(command, check=True)
    return wav_path


class Music2EmoRunner:
    def __init__(self) -> None:
        settings = get_settings()
        self.repo_path = settings.music2emo_repo_path
        repo_path = self.repo_path
        if repo_path is not None and repo_path.exists():
            sys.path.insert(0, str(repo_path))
        try:
            from music2emo import Music2emo
        except ImportError as exc:
            raise RuntimeError(
                "Music2Emo is not importable. Clone https://github.com/AMAAI-Lab/Music2Emotion "
                "and set MUSIC2EMO_REPO_PATH to that repo path before running this job."
            ) from exc
        model_weights = settings.music2emo_model_weights
        if model_weights is None and repo_path is not None:
            model_weights = repo_path / "saved_models" / "J_all.ckpt"
        self.model = Music2emo(model_weights=str(model_weights) if model_weights else "saved_models/J_all.ckpt")

    def predict(self, audio_path: Path) -> dict[str, Any]:
        if self.repo_path is None:
            return self.model.predict(str(audio_path))

        previous_cwd = Path.cwd()
        try:
            os.chdir(self.repo_path)
            return self.model.predict(str(audio_path))
        finally:
            os.chdir(previous_cwd)


def _insert_emotion_result(
    track: dict[str, Any],
    prediction: dict[str, Any],
    inference_seconds: float,
) -> None:
    valence_raw = prediction.get("valence")
    arousal_raw = prediction.get("arousal")
    valence = _normalise_scale_1_to_9(float(valence_raw) if valence_raw is not None else None)
    energy = _normalise_scale_1_to_9(float(arousal_raw) if arousal_raw is not None else None)
    mood_label = _mood_from_valence_energy(valence, energy)
    predicted_moods = prediction.get("predicted_moods") or []

    with db_connection() as connection:
        connection.execute(
            text(
                """
                insert into raw.track_emotion_features (
                    track_id, valence_raw, arousal_raw, valence, energy,
                    mood_label, predicted_moods, model_name, model_version,
                    source_audio_url, inference_seconds, classified_at, error_message
                )
                values (
                    :track_id, :valence_raw, :arousal_raw, :valence, :energy,
                    :mood_label, cast(:predicted_moods as jsonb), :model_name, :model_version,
                    :source_audio_url, :inference_seconds, current_timestamp, null
                )
                on conflict (track_id) do update set
                    valence_raw = excluded.valence_raw,
                    arousal_raw = excluded.arousal_raw,
                    valence = excluded.valence,
                    energy = excluded.energy,
                    mood_label = excluded.mood_label,
                    predicted_moods = excluded.predicted_moods,
                    model_name = excluded.model_name,
                    model_version = excluded.model_version,
                    source_audio_url = excluded.source_audio_url,
                    inference_seconds = excluded.inference_seconds,
                    classified_at = current_timestamp,
                    error_message = null
                """
            ),
            {
                "track_id": track["track_id"],
                "valence_raw": valence_raw,
                "arousal_raw": arousal_raw,
                "valence": valence,
                "energy": energy,
                "mood_label": mood_label,
                "predicted_moods": json.dumps(predicted_moods),
                "model_name": MODEL_NAME,
                "model_version": MODEL_VERSION,
                "source_audio_url": track["preview_url"],
                "inference_seconds": inference_seconds,
            },
        )


def _insert_emotion_failure(track: dict[str, Any], error_message: str) -> None:
    with db_connection() as connection:
        connection.execute(
            text(
                """
                insert into raw.track_emotion_features (
                    track_id, predicted_moods, model_name, model_version,
                    source_audio_url, classified_at, error_message
                )
                values (
                    :track_id, '[]'::jsonb, :model_name, :model_version,
                    :source_audio_url, current_timestamp, :error_message
                )
                on conflict (track_id) do update set
                    model_name = excluded.model_name,
                    model_version = excluded.model_version,
                    source_audio_url = excluded.source_audio_url,
                    classified_at = current_timestamp,
                    error_message = excluded.error_message
                """
            ),
            {
                "track_id": track["track_id"],
                "model_name": MODEL_NAME,
                "model_version": MODEL_VERSION,
                "source_audio_url": track.get("preview_url"),
                "error_message": error_message[:1000],
            },
        )


def run_music2emo_inference(limit: int = 25) -> dict[str, int | float]:
    runner = Music2EmoRunner()
    processed = 0
    failed = 0
    total_seconds = 0.0

    with db_connection() as connection:
        rows = connection.execute(
            text(
                f"""
                select tracks.track_id, tracks.name, tracks.artist_name, tracks.preview_url
                from {qualified_table("dim_tracks")} tracks
                left join raw.track_emotion_features features
                    on tracks.track_id = features.track_id
                where tracks.preview_url is not null
                  and (features.track_id is null or features.error_message is not null)
                order by tracks.artist_name, tracks.name
                limit :limit
                """
            ),
            {"limit": limit},
        ).fetchall()

    for row in rows:
        track = dict(row._mapping)
        preview_path: Path | None = None
        inference_path: Path | None = None
        try:
            preview_path = download_preview(track["preview_url"])
            inference_path = convert_preview_to_wav(preview_path)
            started = time.perf_counter()
            prediction = runner.predict(inference_path)
            elapsed = time.perf_counter() - started
            _insert_emotion_result(track, prediction, elapsed)
            total_seconds += elapsed
            processed += 1
        except Exception as exc:  # noqa: BLE001
            failed += 1
            _insert_emotion_failure(track, str(exc))
        finally:
            if inference_path is not None and inference_path != preview_path:
                inference_path.unlink(missing_ok=True)
            if preview_path is not None:
                preview_path.unlink(missing_ok=True)

    if failed:
        send_slack_alert("music2emo", "Music2Emo inference failures", failed)

    return {
        "processed": processed,
        "failed": failed,
        "avg_inference_seconds": total_seconds / processed if processed else 0.0,
    }
