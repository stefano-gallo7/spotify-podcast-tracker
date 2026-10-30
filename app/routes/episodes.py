from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import not_
from sqlalchemy.orm import Session, contains_eager

from app.db import get_session
from app.db_models import Episode, Show
from app.schemas import EpisodeDetail, EpisodeUpdate, ShowStatus

router = APIRouter(prefix="/api/episodes", tags=["episodes"])


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@router.get("", response_model=list[EpisodeDetail])
def list_episodes(
    session: Session = Depends(get_session),
    in_progress: bool | None = Query(None, description="Only started-but-unfinished episodes (true), or the rest (false)"),
    show_status: ShowStatus | None = Query(None, description="Filter by the parent show's status"),
    limit: int = Query(20, ge=1, le=100, description="Max episodes returned"),
):
    # Joined (not lazy-loaded) so each EpisodeDetail's embedded show costs no
    # extra query, and so show_status can filter on it.
    query = (
        session.query(Episode)
        .join(Episode.show)
        .options(contains_eager(Episode.show))
    )
    if in_progress is not None:
        query = query.filter(Episode.is_in_progress if in_progress else not_(Episode.is_in_progress))
    if show_status is not None:
        query = query.filter(Show.status == show_status)

    return (
        query.order_by(Episode.last_played_at.desc().nulls_last(), Episode.release_date.desc())
        .limit(limit)
        .all()
    )


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
