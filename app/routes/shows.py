from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db import get_session
from app.db_models import Show, Tag
from app.schemas import PaginatedShows, ShowDetail

router = APIRouter(prefix="/api/shows", tags=["shows"])

ShowStatus = Literal["active", "finished", "dropped", "paused"]
SortKey = Literal["name", "listened_count", "total_episodes", "last_played"]
SortOrder = Literal["asc", "desc"]


@router.get("", response_model=PaginatedShows)
def list_shows(
    session: Session = Depends(get_session),
    q: str | None = Query(None, description="Broad search across name, description, and tag names"),
    name: str | None = Query(None, description="Substring match on the show name only"),
    status: ShowStatus | None = Query(None, description="Filter by tracking status"),
    has_more: bool | None = Query(None, description="Only shows with unheard episodes (true) or fully heard (false)"),
    is_favorite: bool | None = Query(None, description="Filter favorites"),
    sort: SortKey = Query("name", description="Sort key"),
    order: SortOrder = Query("asc", description="Sort direction"),
    limit: int = Query(20, ge=1, le=100, description="Page size"),
    offset: int = Query(0, ge=0, description="Page start"),
):
    query = session.query(Show)

    if q:
        pattern = f"%{q}%"
        query = query.filter(
            or_(
                Show.name.ilike(pattern),
                Show.description.ilike(pattern),
                Show.tags.any(Tag.name.ilike(pattern)),
            )
        )
    if name:
        query = query.filter(Show.name.ilike(f"%{name}%"))
    if status is not None:
        query = query.filter(Show.status == status)
    if has_more is not None:
        query = query.filter(Show.has_more_episodes if has_more else ~Show.has_more_episodes)
    if is_favorite is not None:
        query = query.filter(Show.is_favorite == is_favorite)

    total = query.count()

    sort_columns = {
        "name": Show.name,
        "listened_count": Show.listened_count,
        "total_episodes": Show.total_episodes,
        "last_played": Show.last_played_at,
    }
    column = sort_columns[sort]
    query = query.order_by(column.desc() if order == "desc" else column.asc())

    items = query.limit(limit).offset(offset).all()
    return {"items": items, "total": total, "limit": limit, "offset": offset}


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
