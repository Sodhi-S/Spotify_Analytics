from __future__ import annotations

from typing import Any
from urllib.parse import quote_plus

from app.ingestion.http import get_json
from app.ingestion.rate_limiter import RateLimiter

ITUNES_SEARCH_URL = "https://itunes.apple.com/search"


class ITunesClient:
    def __init__(self) -> None:
        self.rate_limiter = RateLimiter(calls_per_second=1 / 3)

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        payload = get_json(
            ITUNES_SEARCH_URL,
            {
                "term": query,
                "entity": "song",
                "limit": limit,
            },
            rate_limiter=self.rate_limiter,
        )
        results = payload.get("results", [])
        return results if isinstance(results, list) else []

    def get_preview_url(self, artist_name: str, track_name: str) -> str | None:
        results = self.search(f"{artist_name} {track_name}")
        if not results:
            return None

        top_result = results[0]
        returned_artist = str(top_result.get("artistName", "")).lower()
        if artist_name.lower() not in returned_artist:
            return None
        preview_url = top_result.get("previewUrl")
        return str(preview_url) if preview_url else None


def search_url_for_display(artist_name: str, track_name: str) -> str:
    return f"{ITUNES_SEARCH_URL}?term={quote_plus(f'{artist_name} {track_name}')}&entity=song"
