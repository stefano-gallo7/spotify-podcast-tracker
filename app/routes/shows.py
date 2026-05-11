from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_session
from app.db_models import Episode, Show
from app.schemas import ShowDetail, ShowSummary

router = APIRouter(prefix="/api/shows", tags=["shows"])


@router.get("", response_model=list[ShowSummary])
def list_shows(session: Session = Depends(get_session)):
    return session.query(Show).order_by(Show.name).all()


@router.get("/{show_id}", response_model=ShowDetail)
def get_show(show_id: int, session: Session = Depends(get_session)):
    show = session.query(Show).filter(Show.id == show_id).first()
    if show is None:
        raise HTTPException(status_code=404, detail="Show not found")

    show.episodes.sort(
        key=lambda e: (e.release_date is None, e.release_date),
        reverse=True,
    )
    return show
