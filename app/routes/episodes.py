from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_session
from app.db_models import Episode
from app.schemas import EpisodeDetail, EpisodeUpdate

router = APIRouter(prefix="/api/episodes", tags=["episodes"])


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@router.get("/{episode_id}", response_model=EpisodeDetail)
def get_episode(episode_id: str, session: Session = Depends(get_session)):
    uri = f"spotify:episode:{episode_id}"
    episode = session.query(Episode).filter(Episode.uri == uri).first()
    if episode is None:
        raise HTTPException(status_code=404, detail="Episode not found")
    return episode


@router.patch("/{episode_id}", response_model=EpisodeDetail)
def update_episode(
    episode_id: str,
    update: EpisodeUpdate,
    session: Session = Depends(get_session),
):
    uri = f"spotify:episode:{episode_id}"
    episode = session.query(Episode).filter(Episode.uri == uri).first()
    if episode is None:
        raise HTTPException(status_code=404, detail="Episode not found")

    update_data = update.model_dump(exclude_unset=True)
    if "rating" in update_data and update_data["rating"] != episode.rating:
        episode.rated_at = _now()
    for field, value in update_data.items():
        setattr(episode, field, value)

    session.commit()
    session.refresh(episode)
    return episode
