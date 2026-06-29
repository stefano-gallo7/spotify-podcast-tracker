from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ShowStatus = Literal["active", "finished", "dropped", "paused"]


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


class ShowUpdate(BaseModel):
    """Partial update for a Show. All fields optional."""

    status: ShowStatus | None = None
    is_favorite: bool | None = None
    notes: str | None = None


class EpisodeUpdate(BaseModel):
    """Partial update for an Episode. All fields optional."""

    rating: int | None = Field(None, ge=1, le=5)
    is_favorite: bool | None = None
    is_archived: bool | None = None
    notes: str | None = None


class SpotifySearchResult(BaseModel):
    """One show from a Spotify catalogue search, shaped for the add-show modal."""

    id: str  # bare Spotify ID (URI's last segment)
    uri: str  # full spotify:show:...
    name: str
    description_excerpt: str | None = None
    image_url_small: str | None = None
    total_episodes: int | None = None
    already_in_library: bool


class AddShowRequest(BaseModel):
    """Request body for adding a show to the library by its Spotify URI."""

    uri: str


class Settings(BaseModel):
    """User-tunable app settings (the configurable subset of AppState).

    Flat, to match the generic-PATCH convention. Today these are all about the
    scheduled refresh; the route is deliberately `/api/settings` so it can grow
    into a comprehensive settings surface, with grouping done presentationally.
    """

    model_config = ConfigDict(from_attributes=True)

    refresh_active_interval_days: int
    refresh_paused_interval_days: int
    refresh_finished_interval_days: int
    auto_finish_enabled: bool
    auto_pause_enabled: bool
    auto_pause_after_days: int
    auto_reactivate_enabled: bool
    scheduler_enabled: bool
    scheduler_run_hour: int


class SettingsUpdate(BaseModel):
    """Partial update for app settings. All fields optional."""

    refresh_active_interval_days: int | None = Field(None, ge=1)
    refresh_paused_interval_days: int | None = Field(None, ge=1)
    refresh_finished_interval_days: int | None = Field(None, ge=1)
    auto_finish_enabled: bool | None = None
    auto_pause_enabled: bool | None = None
    auto_pause_after_days: int | None = Field(None, ge=1)
    auto_reactivate_enabled: bool | None = None
    scheduler_enabled: bool | None = None
    scheduler_run_hour: int | None = Field(None, ge=0, le=23)
