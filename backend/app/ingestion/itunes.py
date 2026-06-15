from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any
from urllib.parse import quote_plus, urlparse

from app.ingestion.http import get_json
from app.ingestion.rate_limiter import RateLimiter

ITUNES_SEARCH_URL = "https://itunes.apple.com/search"
ITUNES_LOOKUP_URL = "https://itunes.apple.com/lookup"
APPLE_MUSIC_ID_PATTERN = re.compile(r"/(?:song|album)/[^/?#]+/(\d+)")

FEATURE_PATTERN = re.compile(
    r"\s*[\(\[]\s*(feat\.?|featuring|ft\.?|with)\s+[^)\]]+[\)\]]",
    re.IGNORECASE,
)
VERSION_PATTERN = re.compile(
    r"\s*[\(\[]\s*(remaster(ed)?|deluxe|explicit|clean|bonus track|radio edit|single version|"
    r"album version|sped up|slowed|reverb|instrumental|live)[^)\]]*[\)\]]",
    re.IGNORECASE,
)
PUNCTUATION_PATTERN = re.compile(r"[^a-z0-9]+")


def _clean_title(value: str) -> str:
    cleaned = FEATURE_PATTERN.sub("", value)
    cleaned = VERSION_PATTERN.sub("", cleaned)
    return cleaned.strip()


def _normalise(value: str) -> str:
    cleaned = _clean_title(value).lower().replace("&", "and")
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


class ITunesClient:
    def __init__(self) -> None:
        self.rate_limiter = RateLimiter(calls_per_second=1 / 3)

    def search(self, query: str, limit: int = 25) -> list[dict[str, Any]]:
        payload = get_json(
            ITUNES_SEARCH_URL,
            {
                "term": query,
                "media": "music",
                "entity": "song",
                "limit": limit,
                "country": "US",
            },
            rate_limiter=self.rate_limiter,
        )
        results = payload.get("results", [])
        return results if isinstance(results, list) else []

    def lookup(self, track_id: str) -> dict[str, Any] | None:
        payload = get_json(
            ITUNES_LOOKUP_URL,
            {
                "id": track_id,
                "entity": "song",
                "country": "US",
            },
            rate_limiter=self.rate_limiter,
        )
        results = payload.get("results", [])
        if not isinstance(results, list):
            return None
        for result in results:
            if str(result.get("wrapperType")) == "track":
                return result
        return None

    def get_preview_url_from_apple_music_url(self, apple_music_url: str) -> str | None:
        track_id = apple_music_track_id(apple_music_url)
        if track_id is None:
            return None
        result = self.lookup(track_id)
        if result is None:
            return None
        preview_url = result.get("previewUrl")
        return str(preview_url) if preview_url else None

    def _queries(self, artist_name: str, track_name: str) -> list[str]:
        clean_track = _clean_title(track_name)
        queries = [
            f"{artist_name} {track_name}",
            f"{artist_name} {clean_track}",
            f"{clean_track} {artist_name}",
            f"{track_name}",
            f"{clean_track}",
        ]
        deduped: list[str] = []
        seen: set[str] = set()
        for query in queries:
            key = query.lower().strip()
            if key and key not in seen:
                seen.add(key)
                deduped.append(query)
        return deduped

    def get_preview_url(self, artist_name: str, track_name: str) -> str | None:
        match = self.get_best_match(artist_name, track_name)
        if match is None:
            return None
        preview_url = match.get("previewUrl")
        return str(preview_url) if preview_url else None

    def get_best_match(self, artist_name: str, track_name: str) -> dict[str, Any] | None:
        best_result: dict[str, Any] | None = None
        best_score = 0.0

        for query in self._queries(artist_name, track_name):
            for result in self.search(query):
                preview_url = result.get("previewUrl")
                if not preview_url:
                    continue

                returned_artist = str(result.get("artistName", ""))
                returned_track = str(result.get("trackName", ""))
                artist_score = _ratio(artist_name, returned_artist)
                track_score = _ratio(track_name, returned_track)
                clean_track_score = _ratio(_clean_title(track_name), returned_track)
                score = (artist_score * 0.45) + (max(track_score, clean_track_score) * 0.55)

                if score > best_score:
                    best_score = score
                    best_result = result

        if best_result is None or best_score < 0.72:
            return None
        best_result["_match_score"] = round(best_score, 3)
        return best_result

    def get_album_artwork_from_apple_music_url(self, apple_music_url: str) -> dict[str, Any] | None:
        track_id = apple_music_track_id(apple_music_url)
        if track_id is None:
            return None
        result = self.lookup(track_id)
        if result is None or not result.get("artworkUrl100"):
            return None
        return result

    def get_best_artwork_match(
        self,
        artist_name: str,
        track_name: str,
        album_name: str | None = None,
    ) -> dict[str, Any] | None:
        best_result: dict[str, Any] | None = None
        best_score = 0.0

        queries = self._queries(artist_name, f"{track_name} {album_name or ''}".strip())
        for query in queries:
            for result in self.search(query):
                if not result.get("artworkUrl100"):
                    continue

                returned_artist = str(result.get("artistName", ""))
                returned_track = str(result.get("trackName", ""))
                returned_album = str(result.get("collectionName", ""))
                artist_score = _ratio(artist_name, returned_artist)
                track_score = max(_ratio(track_name, returned_track), _ratio(_clean_title(track_name), returned_track))
                album_score = _ratio(album_name or "", returned_album) if album_name else 0.0

                if artist_score < 0.82 or track_score < 0.78:
                    continue

                score = (artist_score * 0.44) + (track_score * 0.46)
                if album_name:
                    score += album_score * 0.10

                if score > best_score:
                    best_score = score
                    best_result = result

        if best_result is None or best_score < 0.80:
            return None
        best_result["_match_score"] = round(best_score, 3)
        return best_result


def search_url_for_display(artist_name: str, track_name: str) -> str:
    return f"{ITUNES_SEARCH_URL}?term={quote_plus(f'{artist_name} {track_name}')}&entity=song"


def apple_music_track_id(apple_music_url: str) -> str | None:
    parsed = urlparse(apple_music_url)
    query_params = dict(
        part.split("=", 1)
        for part in parsed.query.split("&")
        if "=" in part
    )
    if query_params.get("i"):
        return query_params["i"]

    match = APPLE_MUSIC_ID_PATTERN.search(parsed.path)
    return match.group(1) if match else None
