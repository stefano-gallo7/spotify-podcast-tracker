from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class TagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str


class ShowSummary(BaseModel):
    """Slim view of a Show, used in list endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    image_url_medium: str | None = None
    spotify_url: str | None = None
    total_episodes: int | None = None
    listened_count: int
    has_more_episodes: bool
    last_played_at: datetime | None = None
    status: str
    is_favorite: bool


class PaginatedShows(BaseModel):
    """Wrapper for a page of shows plus pagination metadata."""

    items: list[ShowSummary]
    total: int
    limit: int
    offset: int


class EpisodeSummary(BaseModel):
    """Slim view of an Episode, used inside ShowDetail."""

    model_config = ConfigDict(from_attributes=True)

    uri: str
    id: str
    name: str
    duration_ms: int | None = None
    release_date: date | None = None
    image_url_medium: str | None = None
    spotify_url: str | None = None
    is_fully_played: bool
    resume_position_ms: int | None = None
    last_played_at: datetime | None = None
    rating: int | None = None
    is_favorite: bool


class ShowDetail(ShowSummary):
    """Full view of a Show, including episodes and tags."""

    image_url_big: str | None = None
    name_from_export: str | None = None
    languages: str | None = None
    explicit: bool | None = None
    has_new_episodes: bool
    notes: str | None = None
    tags: list[TagOut] = []
    episodes: list[EpisodeSummary] = []


class ShowReference(BaseModel):
    """Minimal show info, used as a back-reference from EpisodeDetail."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    image_url_small: str | None = None


class EpisodeDetail(EpisodeSummary):
    """Full view of an Episode, including its parent show."""

    description: str | None = None
    languages: str | None = None
    explicit: bool | None = None
    is_playable: bool | None = None
    ms_played: int | None = None
    play_count: int | None = None
    discovered_via: str | None = None
    notes: str | None = None
    is_archived: bool
    show: ShowReference
