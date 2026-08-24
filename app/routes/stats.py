from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, case, func
from sqlalchemy.orm import Session

from app.db import get_session
from app.db_models import Episode, Show, Tag, show_tags
from app.schemas import (
    ActivityPoint,
    RatingCount,
    StatsOverview,
    StatusCount,
    TagStat,
    TopShow,
)

router = APIRouter(prefix="/api/stats", tags=["stats"])

# Protocol-only Literals (live with the route, per convention).
TopShowsBy = Literal["hours", "episodes"]
ActivityMetric = Literal["episodes", "hours"]
TagStatBy = Literal["hours", "episodes"]

# All statuses/ratings we always want present in breakdowns, even at zero.
_ALL_STATUSES = ("active", "finished", "dropped", "paused")
_ALL_RATINGS = (1, 2, 3, 4, 5)


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# Estimated per-episode listening time. Defined once; reused everywhere hours
# appear so the proxy never drifts between endpoints. See DASHBOARD_PLAN.md.
#   measured ms_played -> else episode length if completed -> else how far in -> 0
_ESTIMATED_MS = func.coalesce(
    Episode.ms_played,
    case((Episode.is_fully_played.is_(True), Episode.duration_ms)),
    Episode.resume_position_ms,
    0,
)

# Reusable per-row "counts as one fully-played episode" (0/1) sum term.
_PLAYED_1 = case((Episode.is_fully_played.is_(True), 1), else_=0)


@router.get("/overview", response_model=StatsOverview)
def overview(session: Session = Depends(get_session)):
    ep = session.query(
        func.count().label("total_episodes"),
        func.coalesce(func.sum(_ESTIMATED_MS), 0).label("estimated_ms_played"),
        func.coalesce(func.sum(func.coalesce(Episode.ms_played, 0)), 0).label("measured_ms_played"),
        func.coalesce(func.sum(
            case((and_(Episode.ms_played.is_(None), Episode.is_fully_played.is_(True)), 1), else_=0)
        ), 0).label("estimated_from_duration_count"),
        func.coalesce(func.sum(_PLAYED_1), 0).label("episodes_played"),
        func.coalesce(func.sum(
            case((and_(Episode.resume_position_ms.isnot(None), Episode.is_fully_played.is_(False)), 1), else_=0)
        ), 0).label("episodes_in_progress"),
        func.coalesce(func.sum(case((Episode.is_favorite.is_(True), 1), else_=0)), 0).label("favorite_episodes"),
        func.avg(Episode.rating).label("average_rating"),
        func.coalesce(func.sum(case((Episode.rating.isnot(None), 1), else_=0)), 0).label("rated_count"),
    ).one()

    total_shows = session.query(func.count(Show.id)).scalar() or 0
    favorite_shows = (
        session.query(func.count(Show.id)).filter(Show.is_favorite.is_(True)).scalar() or 0
    )

    status_rows = dict(
        session.query(Show.status, func.count(Show.id)).group_by(Show.status).all()
    )
    status_breakdown = [
        StatusCount(status=s, count=status_rows.get(s, 0)) for s in _ALL_STATUSES
    ]

    rating_rows = dict(
        session.query(Episode.rating, func.count())
        .filter(Episode.rating.isnot(None))
        .group_by(Episode.rating)
        .all()
    )
    ratings_distribution = [
        RatingCount(rating=r, count=rating_rows.get(r, 0)) for r in _ALL_RATINGS
    ]

    return StatsOverview(
        estimated_ms_played=int(ep.estimated_ms_played),
        measured_ms_played=int(ep.measured_ms_played),
        estimated_from_duration_count=int(ep.estimated_from_duration_count),
        episodes_played=int(ep.episodes_played),
        episodes_in_progress=int(ep.episodes_in_progress),
        total_episodes=int(ep.total_episodes),
        total_shows=int(total_shows),
        favorite_shows=int(favorite_shows),
        favorite_episodes=int(ep.favorite_episodes),
        average_rating=float(ep.average_rating) if ep.average_rating is not None else None,
        rated_count=int(ep.rated_count),
        unrated_count=int(ep.total_episodes) - int(ep.rated_count),
        status_breakdown=status_breakdown,
        ratings_distribution=ratings_distribution,
    )


@router.get("/top-shows", response_model=list[TopShow])
def top_shows(
    session: Session = Depends(get_session),
    limit: int = Query(10, ge=1, le=50),
    by: TopShowsBy = Query("hours"),
):
    est_sum = func.coalesce(func.sum(_ESTIMATED_MS), 0)
    played_sum = func.coalesce(func.sum(_PLAYED_1), 0)

    q = (
        session.query(
            Show.id,
            Show.name,
            Show.image_url_small,
            est_sum.label("estimated_ms_played"),
            played_sum.label("listened_count"),
        )
        .join(Episode, Episode.show_id == Show.id)
        .group_by(Show.id)
    )

    # Filter out shows with nothing to rank on, then order by the chosen metric.
    if by == "hours":
        q = q.having(est_sum > 0).order_by(est_sum.desc())
    else:
        q = q.having(played_sum > 0).order_by(played_sum.desc())

    rows = q.limit(limit).all()
    return [
        TopShow(
            id=r.id,
            name=r.name,
            image_url_small=r.image_url_small,
            estimated_ms_played=int(r.estimated_ms_played),
            listened_count=int(r.listened_count),
        )
        for r in rows
    ]


@router.get("/activity", response_model=list[ActivityPoint])
def activity(
    session: Session = Depends(get_session),
    months: int = Query(12, ge=1, le=60),
    metric: ActivityMetric = Query("episodes"),  # both series returned; hints the default chart
):
    # Window start = first day of the month, (months - 1) months back.
    now = _now()
    total = (now.year * 12 + (now.month - 1)) - (months - 1)
    start_year, start_month = divmod(total, 12)
    start_month += 1
    cutoff = datetime(start_year, start_month, 1)

    month_expr = func.strftime("%Y-%m", Episode.last_played_at)
    rows = dict(
        (m, (episodes, est))
        for m, episodes, est in session.query(
            month_expr.label("month"),
            func.count().label("episodes"),
            func.coalesce(func.sum(_ESTIMATED_MS), 0).label("estimated_ms"),
        )
        .filter(Episode.last_played_at.isnot(None), Episode.last_played_at >= cutoff)
        .group_by(month_expr)
        .all()
    )

    # Gap-fill a continuous month series so the line chart has no holes.
    points: list[ActivityPoint] = []
    y, m = start_year, start_month
    while (y, m) <= (now.year, now.month):
        label = f"{y:04d}-{m:02d}"
        episodes, est = rows.get(label, (0, 0))
        points.append(ActivityPoint(month=label, episodes=int(episodes), estimated_ms=int(est)))
        m += 1
        if m > 12:
            m, y = 1, y + 1
    return points


@router.get("/by-tag", response_model=list[TagStat])
def by_tag(
    session: Session = Depends(get_session),
    by: TagStatBy = Query("hours"),
):
    est_sum = func.coalesce(func.sum(_ESTIMATED_MS), 0)
    played_sum = func.coalesce(func.sum(_PLAYED_1), 0)

    q = (
        session.query(
            Tag.name.label("tag"),
            func.count(func.distinct(Show.id)).label("shows"),
            played_sum.label("episodes_played"),
            est_sum.label("estimated_ms_played"),
        )
        .join(show_tags, show_tags.c.tag_id == Tag.id)
        .join(Show, Show.id == show_tags.c.show_id)
        .join(Episode, Episode.show_id == Show.id)
        .group_by(Tag.id)
    )
    q = q.order_by(est_sum.desc() if by == "hours" else played_sum.desc())

    # Returns [] when no tags exist; the frontend omits the section entirely.
    return [
        TagStat(
            tag=r.tag,
            shows=int(r.shows),
            episodes_played=int(r.episodes_played),
            estimated_ms_played=int(r.estimated_ms_played),
        )
        for r in q.all()
    ]
