from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone
from typing import Any

from app.core.config import get_settings
from app.ingestion.http import get_json
from app.ingestion.rate_limiter import RateLimiter

LASTFM_BASE_URL = "https://ws.audioscrobbler.com/2.0/"


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _text(value: Any) -> str | None:
    if isinstance(value, dict):
        raw = value.get("#text")
        return str(raw).strip() if raw else None
    if value is None:
        return None
    return str(value).strip() or None


def _int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


class LastFmClient:
    def __init__(self, api_key: str | None = None, username: str | None = None):
        settings = get_settings()
        self.api_key = api_key or settings.lastfm_api_key
        self.username = username or settings.lastfm_username
        self.rate_limiter = RateLimiter(calls_per_second=5)

    def request(self, method: str, **params: Any) -> dict[str, Any]:
        merged = {
            "method": method,
            "api_key": self.api_key,
            "format": "json",
            **params,
        }
        return get_json(LASTFM_BASE_URL, merged, rate_limiter=self.rate_limiter)

    def iter_recent_tracks(self, from_unix: int | None = None) -> Iterator[dict[str, Any]]:
        page = 1
        while True:
            params: dict[str, Any] = {
                "user": self.username,
                "page": page,
                "limit": 200,
            }
            if from_unix is not None:
                params["from"] = from_unix

            payload = self.request("user.getRecentTracks", **params)
            recent = payload.get("recenttracks", {})
            tracks = _as_list(recent.get("track"))
            attrs = recent.get("@attr", {})
            total_pages = int(attrs.get("totalPages") or page)

            for track in tracks:
                if isinstance(track, dict):
                    yield track

            if page >= total_pages:
                break
            page += 1

    def get_track_tags(self, artist_name: str, track_name: str) -> list[dict[str, Any]]:
        payload = self.request(
            "track.getTopTags",
            artist=artist_name,
            track=track_name,
            autocorrect=1,
        )
        return normalize_tags(payload.get("toptags", {}).get("tag"))

    def get_artist_info(self, artist_name: str) -> dict[str, Any]:
        return self.request("artist.getInfo", artist=artist_name, autocorrect=1)

    def get_artist_tags(self, artist_name: str) -> list[dict[str, Any]]:
        payload = self.request("artist.getTopTags", artist=artist_name, autocorrect=1)
        return normalize_tags(payload.get("toptags", {}).get("tag"))

    def get_top_artists(self, period: str = "overall", limit: int = 50) -> list[dict[str, Any]]:
        payload = self.request(
            "user.getTopArtists",
            user=self.username,
            period=period,
            limit=limit,
        )
        return _as_list(payload.get("topartists", {}).get("artist"))

    def get_top_tracks(self, period: str = "overall", limit: int = 50) -> list[dict[str, Any]]:
        payload = self.request(
            "user.getTopTracks",
            user=self.username,
            period=period,
            limit=limit,
        )
        return _as_list(payload.get("toptracks", {}).get("track"))


def normalize_recent_track(payload: dict[str, Any]) -> dict[str, Any] | None:
    if payload.get("@attr", {}).get("nowplaying") == "true":
        return None

    played = payload.get("date", {})
    played_uts = played.get("uts")
    if not played_uts:
        raise ValueError("recent track payload is missing date.uts")

    track_name = _text(payload.get("name"))
    artist_name = _text(payload.get("artist"))
    if not track_name or not artist_name:
        raise ValueError("recent track payload is missing track or artist")

    return {
        "track_name": track_name,
        "artist_name": artist_name,
        "album": _text(payload.get("album")),
        "played_at": datetime.fromtimestamp(int(played_uts), tz=timezone.utc),
        "track_mbid": _text(payload.get("mbid")),
        "artist_mbid": _text(payload.get("artist", {}).get("mbid")),
        "raw_payload": payload,
    }


def normalize_artist_info(payload: dict[str, Any]) -> dict[str, Any]:
    artist = payload.get("artist")
    if not isinstance(artist, dict):
        raise ValueError("artist.getInfo response is missing artist")

    artist_name = _text(artist.get("name"))
    if not artist_name:
        raise ValueError("artist.getInfo response is missing artist.name")

    stats = artist.get("stats") if isinstance(artist.get("stats"), dict) else {}
    similar = artist.get("similar", {}) if isinstance(artist.get("similar"), dict) else {}
    bio = artist.get("bio", {}) if isinstance(artist.get("bio"), dict) else {}

    return {
        "artist_name": artist_name,
        "artist_mbid": _text(artist.get("mbid")),
        "listener_count": _int(stats.get("listeners")),
        "play_count": _int(stats.get("playcount")),
        "similar_artists": [
            {"name": _text(item.get("name")), "mbid": _text(item.get("mbid"))}
            for item in _as_list(similar.get("artist"))
            if isinstance(item, dict)
        ],
        "bio": _text(bio.get("summary")),
        "raw_payload": payload,
    }


def normalize_tags(value: Any) -> list[dict[str, Any]]:
    tags: list[dict[str, Any]] = []
    for item in _as_list(value):
        if not isinstance(item, dict):
            continue
        name = _text(item.get("name"))
        if name:
            tags.append({"name": name.lower().strip(), "count": _int(item.get("count")) or 0})
    return tags
