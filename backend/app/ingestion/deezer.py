from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

from app.ingestion.http import get_json
from app.ingestion.rate_limiter import RateLimiter

DEEZER_ARTIST_SEARCH_URL = "https://api.deezer.com/search/artist"
PUNCTUATION_PATTERN = re.compile(r"[^a-z0-9]+")


def _normalise(value: str) -> str:
    cleaned = value.lower().replace("&", "and")
    return PUNCTUATION_PATTERN.sub(" ", cleaned).strip()


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


def _usable_picture(value: Any) -> str | None:
    if not value:
        return None
    url = str(value)
    if "/images/artist//" in url:
        return None
    return url


class DeezerClient:
    def __init__(self) -> None:
        self.rate_limiter = RateLimiter(calls_per_second=2)

    def search_artists(self, artist_name: str, limit: int = 10) -> list[dict[str, Any]]:
        payload = get_json(
            DEEZER_ARTIST_SEARCH_URL,
            {
                "q": artist_name,
                "limit": limit,
            },
            rate_limiter=self.rate_limiter,
        )
        results = payload.get("data", [])
        return results if isinstance(results, list) else []

    def get_best_artist_image(self, artist_name: str) -> dict[str, Any] | None:
        best_result: dict[str, Any] | None = None
        best_score = 0.0

        for result in self.search_artists(artist_name):
            returned_name = str(result.get("name", ""))
            score = _ratio(artist_name, returned_name)
            image_url = (
                _usable_picture(result.get("picture_xl"))
                or _usable_picture(result.get("picture_big"))
                or _usable_picture(result.get("picture_medium"))
            )
            if image_url is None or score < 0.84:
                continue
            if score > best_score:
                best_score = score
                best_result = {
                    **result,
                    "_match_score": round(score, 3),
                    "_selected_image_url": image_url,
                }

        return best_result
