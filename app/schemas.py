from pydantic import BaseModel, ConfigDict


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
    status: str
    is_favorite: bool
