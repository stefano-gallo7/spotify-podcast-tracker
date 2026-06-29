from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db import SessionLocal, get_session
from app.db_models import Show, Tag
from app.schemas import AddShowRequest, PaginatedShows, ShowDetail, ShowStatus, ShowSummary, ShowUpdate
from app.spotify import call_with_retry, make_client, populate_show, sync_show_episodes

router = APIRouter(prefix="/api/shows", tags=["shows"])

SortKey = Literal["name", "listened_count", "total_episodes", "last_played"]
SortOrder = Literal["asc", "desc"]


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _scan_episodes(show_id: int) -> None:
    """Background job: scan a freshly added show for already-played episodes.

    Runs *after* the POST response is sent, so it owns its own DB session and
    Spotify client — the request's session is already closed by this point.
    """
    session = SessionLocal()
    try:
        show = session.query(Show).filter(Show.id == show_id).first()
        if show is None:
            return
        sp = make_client()
        stats = {"episodes_inserted": 0, "episodes_updated": 0}
        sync_show_episodes(sp, session, show, stats)
        session.commit()
    finally:
        session.close()


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


@router.post("", response_model=ShowSummary, status_code=201)
def add_show(
    body: AddShowRequest,
    background_tasks: BackgroundTasks,
    response: Response,
    session: Session = Depends(get_session),
):
    uri = body.uri
    if not uri.startswith("spotify:show:"):
        raise HTTPException(status_code=422, detail="uri must start with 'spotify:show:'")

    # Idempotent: adding a show that's already tracked returns it unchanged (200).
    existing = session.query(Show).filter(Show.uri == uri).first()
    if existing is not None:
        response.status_code = 200
        return existing

    show_data = call_with_retry(make_client().show, uri)
    show = Show(status="active")
    populate_show(show, show_data)
    session.add(show)
    session.commit()
    session.refresh(show)

    # Scan for already-played episodes after the response is sent.
    background_tasks.add_task(_scan_episodes, show.id)
    return show


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


@router.patch("/{show_id}", response_model=ShowDetail)
def update_show(
    show_id: int,
    update: ShowUpdate,
    session: Session = Depends(get_session),
):
    show = session.query(Show).filter(Show.id == show_id).first()
    if show is None:
        raise HTTPException(status_code=404, detail="Show not found")

    update_data = update.model_dump(exclude_unset=True)
    if "status" in update_data and update_data["status"] != show.status:
        show.status_changed_at = _now()
    for field, value in update_data.items():
        setattr(show, field, value)

    session.commit()
    session.refresh(show)

    show.episodes.sort(
        key=lambda e: (e.release_date is None, e.release_date),
        reverse=True,
    )
    return show
