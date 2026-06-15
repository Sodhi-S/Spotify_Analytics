from __future__ import annotations

import re
import shutil
import subprocess
from difflib import SequenceMatcher
from typing import Any

from app.core.config import ROOT_DIR, get_settings
from app.db import db_connection
from app.ingestion.itunes import ITunesClient
from app.ingestion.lastfm import LastFmClient, normalize_artist_info
from app.ingestion.loader import RawLoader

ARTWORK_SIZE = 600
ARTWORK_SIZE_PATTERN = re.compile(r"\d+x\d+bb")
LASTFM_SIZE_ORDER = {
    "small": 0,
    "medium": 1,
    "large": 2,
    "extralarge": 3,
    "mega": 4,
}
LASTFM_PLACEHOLDER_TOKEN = "2a96cbd8b46e442fc41c2b86b821562f"
PUNCTUATION_PATTERN = re.compile(r"[^a-z0-9]+")


def _normalise(value: str) -> str:
    return PUNCTUATION_PATTERN.sub(" ", value.lower().replace("&", "and")).strip()


def _ratio(left: str, right: str) -> float:
    left_norm = _normalise(left)
    right_norm = _normalise(right)
    if not left_norm or not right_norm:
        return 0.0
    if left_norm == right_norm:
        return 1.0
    if left_norm in right_norm or right_norm in left_norm:
        return 0.92
    return SequenceMatcher(None, left_norm, right_norm).ratio()


def _sized_itunes_artwork_url(value: Any) -> str | None:
    if not value:
        return None
    url = str(value)
    sized = ARTWORK_SIZE_PATTERN.sub(f"{ARTWORK_SIZE}x{ARTWORK_SIZE}bb", url)
    return sized or url


def _lastfm_payload_artist(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    artist = payload.get("artist")
    return artist if isinstance(artist, dict) else None


def _lastfm_artist_image(payload: Any) -> tuple[str, int | None, int | None] | None:
    artist = _lastfm_payload_artist(payload)
    if artist is None:
        return None
    images = artist.get("image")
    if not isinstance(images, list):
        return None

    candidates: list[tuple[int, str, str | None]] = []
    for image in images:
        if not isinstance(image, dict):
            continue
        url = str(image.get("#text") or "").strip()
        if not url or LASTFM_PLACEHOLDER_TOKEN in url:
            continue
        size = str(image.get("size") or "").lower()
        candidates.append((LASTFM_SIZE_ORDER.get(size, -1), url, size))

    if not candidates:
        return None

    _, url, size = max(candidates, key=lambda item: item[0])
    if size == "mega":
        return url, 300, 300
    if size == "extralarge":
        return url, 300, 300
    if size == "large":
        return url, 174, 174
    if size == "medium":
        return url, 64, 64
    if size == "small":
        return url, 34, 34
    return url, None, None


def _lastfm_artist_name(payload: Any) -> str | None:
    artist = _lastfm_payload_artist(payload)
    if artist is None:
        return None
    name = artist.get("name")
    return str(name).strip() if name else None


def _can_request_lastfm() -> bool:
    settings = get_settings()
    return bool(settings.lastfm_api_key)


def enrich_track_images(
    limit: int = 100,
    refresh: bool = False,
    retry_unresolved: bool = False,
) -> dict[str, int]:
    client = ITunesClient()
    inspected = 0
    found = 0
    unresolved = 0

    with db_connection() as connection:
        loader = RawLoader(connection)
        loader.ensure_image_enrichment_tables()
        for track in loader.missing_track_image_targets(
            limit=limit,
            refresh=refresh,
            retry_unresolved=retry_unresolved,
        ):
            inspected += 1
            try:
                result = client.get_best_artwork_match(
                    track["artist_name"],
                    track["track_name"],
                    track.get("album"),
                )
                image_url = _sized_itunes_artwork_url(result.get("artworkUrl100") if result else None)
                if image_url:
                    loader.upsert_track_image(
                        track_id=track["track_id"],
                        image_url=image_url,
                        source="itunes",
                        width=ARTWORK_SIZE,
                        height=ARTWORK_SIZE,
                        raw_payload=result,
                    )
                    found += 1
                else:
                    loader.upsert_track_image(
                        track_id=track["track_id"],
                        image_url=None,
                        source=None,
                        width=None,
                        height=None,
                        raw_payload=dict(track),
                        unresolved_reason="No conservative iTunes artwork match found.",
                    )
                    unresolved += 1
            except Exception as exc:  # noqa: BLE001 - persisted for later inspection.
                loader.insert_failed("track_image_enrichment", dict(track), str(exc))
                unresolved += 1

    return {"inspected": inspected, "found": found, "unresolved": unresolved}


def _artist_payload_for_target(
    loader: RawLoader,
    client: LastFmClient | None,
    target: dict[str, Any],
) -> Any:
    payload = target.get("raw_payload")
    if _lastfm_payload_artist(payload) is not None:
        return payload

    if client is None:
        return payload

    artist = normalize_artist_info(client.get_artist_info(target["artist_name"]))
    loader.upsert_artist_info(artist)
    return artist["raw_payload"]


def _artist_album_fallback(loader: RawLoader, target: dict[str, Any]) -> tuple[str, int | None, int | None, dict[str, Any]] | None:
    fallback = loader.artist_album_image_fallback(target["artist_id"])
    if fallback is None or not fallback.get("image_url"):
        return None
    raw_payload = fallback.get("raw_payload")
    if not isinstance(raw_payload, dict):
        raw_payload = {"artist_id": target["artist_id"], "artist_name": target["artist_name"]}
    raw_payload = {
        **raw_payload,
        "_artist_image_fallback": "representative_album_artwork",
    }
    return (
        str(fallback["image_url"]),
        fallback.get("image_width"),
        fallback.get("image_height"),
        raw_payload,
    )


def enrich_artist_images(
    limit: int = 100,
    refresh: bool = False,
    retry_unresolved: bool = False,
    use_album_fallback: bool = True,
) -> dict[str, int]:
    inspected = 0
    found = 0
    unresolved = 0
    client = LastFmClient() if _can_request_lastfm() else None

    with db_connection() as connection:
        loader = RawLoader(connection)
        loader.ensure_image_enrichment_tables()
        for target in loader.missing_artist_image_targets(
            limit=limit,
            refresh=refresh,
            retry_unresolved=retry_unresolved,
        ):
            inspected += 1
            try:
                payload = _artist_payload_for_target(loader, client, target)
                returned_name = _lastfm_artist_name(payload)
                if returned_name and _ratio(target["artist_name"], returned_name) < 0.88:
                    loader.upsert_artist_image(
                        artist_id=target["artist_id"],
                        image_url=None,
                        source=None,
                        width=None,
                        height=None,
                        raw_payload=payload if isinstance(payload, dict) else dict(target),
                        unresolved_reason="Last.fm artist match was ambiguous.",
                    )
                    unresolved += 1
                    continue

                image = _lastfm_artist_image(payload)
                if image is None:
                    fallback = _artist_album_fallback(loader, target) if use_album_fallback else None
                    if fallback is not None:
                        image_url, width, height, raw_payload = fallback
                        loader.upsert_artist_image(
                            artist_id=target["artist_id"],
                            image_url=image_url,
                            source="itunes_album_artwork_fallback",
                            width=width,
                            height=height,
                            raw_payload=raw_payload,
                        )
                        found += 1
                        continue

                    loader.upsert_artist_image(
                        artist_id=target["artist_id"],
                        image_url=None,
                        source=None,
                        width=None,
                        height=None,
                        raw_payload=payload if isinstance(payload, dict) else dict(target),
                        unresolved_reason="No Last.fm artist image found.",
                    )
                    unresolved += 1
                    continue

                image_url, width, height = image
                loader.upsert_artist_image(
                    artist_id=target["artist_id"],
                    image_url=image_url,
                    source="lastfm",
                    width=width,
                    height=height,
                    raw_payload=payload,
                )
                found += 1
            except Exception as exc:  # noqa: BLE001 - persisted for later inspection.
                loader.insert_failed("artist_image_enrichment", dict(target), str(exc))
                unresolved += 1

    return {"inspected": inspected, "found": found, "unresolved": unresolved}


def run_image_enrichment(
    track_limit: int = 100,
    artist_limit: int = 100,
    refresh: bool = False,
    retry_unresolved: bool = False,
    use_album_fallback: bool = True,
) -> dict[str, Any]:
    return {
        "track_images": enrich_track_images(
            limit=track_limit,
            refresh=refresh,
            retry_unresolved=retry_unresolved,
        ),
        "artist_images": enrich_artist_images(
            limit=artist_limit,
            refresh=refresh,
            retry_unresolved=retry_unresolved,
            use_album_fallback=use_album_fallback,
        ),
    }


def _combine_counts(left: dict[str, int], right: dict[str, int]) -> dict[str, int]:
    keys = set(left) | set(right)
    return {key: int(left.get(key, 0)) + int(right.get(key, 0)) for key in keys}


def run_all_image_enrichment(
    batch_size: int = 100,
    refresh: bool = False,
    retry_unresolved: bool = False,
    use_album_fallback: bool = True,
    max_batches: int = 0,
) -> dict[str, Any]:
    totals = {
        "track_images": {"inspected": 0, "found": 0, "unresolved": 0},
        "artist_images": {"inspected": 0, "found": 0, "unresolved": 0},
    }
    batches = 0

    with db_connection() as connection:
        loader = RawLoader(connection)
        loader.ensure_image_enrichment_tables()
        total_targets = (
            loader.count_track_image_targets(refresh=refresh, retry_unresolved=retry_unresolved)
            + loader.count_artist_image_targets(refresh=refresh, retry_unresolved=retry_unresolved)
        )

    while True:
        batches += 1
        result = run_image_enrichment(
            track_limit=batch_size,
            artist_limit=batch_size,
            refresh=refresh and batches == 1,
            retry_unresolved=retry_unresolved,
            use_album_fallback=use_album_fallback,
        )
        totals["track_images"] = _combine_counts(totals["track_images"], result["track_images"])
        totals["artist_images"] = _combine_counts(totals["artist_images"], result["artist_images"])

        inspected = result["track_images"]["inspected"] + result["artist_images"]["inspected"]
        total_inspected = totals["track_images"]["inspected"] + totals["artist_images"]["inspected"]
        if inspected == 0:
            break
        if total_inspected >= total_targets:
            break
        if max_batches and batches >= max_batches:
            break

    return {
        **totals,
        "batches": batches,
        "target_count": total_targets,
    }


def _dbt_executable() -> str:
    configured = get_settings().dbt_executable
    if shutil.which(configured):
        return configured

    local_conda_dbt = "/opt/anaconda3/envs/ve/bin/dbt"
    if shutil.which(local_conda_dbt):
        return local_conda_dbt

    return configured


def rebuild_image_models() -> dict[str, object]:
    command = [
        _dbt_executable(),
        "run",
        "--profiles-dir",
        ".",
        "--select",
        "dim_tracks",
        "dim_artists",
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
