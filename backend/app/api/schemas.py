from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


Period = Literal["7d", "30d", "6m", "all"]


class TopTrack(BaseModel):
    track_id: str
    name: str
    artist_name: str
    play_count: int = Field(ge=0)


class TopArtist(BaseModel):
    artist_id: str
    name: str
    play_count: int = Field(ge=0)


class TopTag(BaseModel):
    tag: str
    listen_count: int = Field(ge=0)


class OverviewResponse(BaseModel):
    period: Period
    total_listens: int = Field(ge=0)
    unique_tracks: int = Field(ge=0)
    unique_artists: int = Field(ge=0)
    top_tracks: list[TopTrack]
    top_artists: list[TopArtist]
    top_tags: list[TopTag]
    mood_breakdown: dict[str, int]
