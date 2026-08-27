from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, case, func
from sqlalchemy.orm import Session

from app.db import get_session
from app.db_models import Episode, Show, Tag, show_tags
from app.schemas import (
    ActivityPoint,
    ActivitySeries,
    RatingCount,
    StatsOverview,
    StatusCount,
    TagStat,
    TopShow,
)

router = APIRouter(prefix="/api/stats", tags=["stats"])

# Protocol-only Literals (live with the route, per convention).
TopShowsBy = Literal["hours", "episodes"]
ActivityResolution = Literal["month", "week"]
TagStatBy = Literal["hours", "episodes"]

# All statuses/ratings we always want present in breakdowns, even at zero.
_ALL_STATUSES = ("active", "finished", "dropped", "paused")
_ALL_RATINGS = (1, 2, 3, 4, 5)


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _month_start(index: int) -> datetime:
    """First day of the month for a year*12+(month-1) index."""
    y, m0 = divmod(index, 12)
    return datetime(y, m0 + 1, 1)


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


@router.get("/activity", response_model=ActivitySeries)
def activity(
    session: Session = Depends(get_session),
    months: int = Query(12, ge=0, le=120, description="Window length in months; 0 = all time"),
    resolution: ActivityResolution = Query("month"),
    end_offset: int = Query(0, ge=0, description="Months to shift the window end back from now; 0 = ends at the current month"),
):
    # Both series (episodes + estimated_ms) are always returned; the client
    # picks which to plot. This is a recency view — each episode lands in one
    # bucket by its single last_played_at, so it approximates, not measures.
    now = _now()
    now_index = now.year * 12 + (now.month - 1)
    earliest = session.query(func.min(Episode.last_played_at)).scalar()

    if months == 0:
        # All time: one window from the earliest play to now; no paging.
        if earliest is None:
            return ActivitySeries(points=[], has_older=False, has_newer=False)
        start_index = earliest.year * 12 + (earliest.month - 1)
        end_index = now_index
        has_older = False
        has_newer = False
    else:
        # The window END is anchored `end_offset` months back from now; the
        # window length only changes how far back `start` reaches. So changing
        # resolution or window length keeps the end fixed (paging is preserved).
        end_index = now_index - end_offset
        start_index = end_index - (months - 1)
        start_dt = _month_start(start_index)
        has_older = earliest is not None and earliest < start_dt
        has_newer = end_offset > 0

    start = _month_start(start_index)
    end_exclusive = _month_start(end_index + 1)  # first day after the window's last month

    # Bucket by month ("YYYY-MM") or by week-start Monday ("YYYY-MM-DD"). ISO
    # week (%V) may be missing on the bundled SQLite, so derive the Monday.
    if resolution == "week":
        bucket_expr = func.date(Episode.last_played_at, "-6 days", "weekday 1")
    else:
        bucket_expr = func.strftime("%Y-%m", Episode.last_played_at)

    rows = dict(
        (bucket, (episodes, est))
        for bucket, episodes, est in session.query(
            bucket_expr.label("bucket"),
            func.count().label("episodes"),
            func.coalesce(func.sum(_ESTIMATED_MS), 0).label("estimated_ms"),
        )
        .filter(
            Episode.last_played_at.isnot(None),
            Episode.last_played_at >= start,
            Episode.last_played_at < end_exclusive,
        )
        .group_by(bucket_expr)
        .all()
    )

    # Gap-fill a continuous series so the line chart has no holes. Cap the tail
    # at `now` so the current window doesn't trail empty future buckets.
    points: list[ActivityPoint] = []
    if resolution == "week":
        last_day = min(end_exclusive - timedelta(days=1), now)
        cur = (start - timedelta(days=start.weekday())).date()  # Monday of start's week
        last = (last_day - timedelta(days=last_day.weekday())).date()
        while cur <= last:
            label = cur.isoformat()
            episodes, est = rows.get(label, (0, 0))
            points.append(ActivityPoint(bucket=label, episodes=int(episodes), estimated_ms=int(est)))
            cur += timedelta(days=7)
    else:
        idx = start_index
        while idx <= end_index:
            label = _month_start(idx).strftime("%Y-%m")
            episodes, est = rows.get(label, (0, 0))
            points.append(ActivityPoint(bucket=label, episodes=int(episodes), estimated_ms=int(est)))
            idx += 1

    return ActivitySeries(
        points=points,
        has_older=has_older,
        has_newer=has_newer,
        start=_month_start(start_index).strftime("%Y-%m"),
        end=_month_start(end_index).strftime("%Y-%m"),
    )


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
