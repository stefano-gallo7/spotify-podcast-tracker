from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_session
from app.db_models import Episode
from app.schemas import EpisodeDetail

router = APIRouter(prefix="/api/episodes", tags=["episodes"])


@router.get("/{episode_id}", response_model=EpisodeDetail)
def get_episode(episode_id: str, session: Session = Depends(get_session)):
    uri = f"spotify:episode:{episode_id}"
    episode = session.query(Episode).filter(Episode.uri == uri).first()
    if episode is None:
        raise HTTPException(status_code=404, detail="Episode not found")
    return episode
