"""
Shared helpers for talking to the Spotify Web API.

Used by both the enrichment script (initial fill-in after import) and the
refresh script (periodic re-sync of metadata + listening progress).
"""

import time
from datetime import date, datetime, timedelta, timezone

import spotipy
from dotenv import load_dotenv
from spotipy.exceptions import SpotifyException
from spotipy.oauth2 import SpotifyOAuth

from app.db_models import AppState, Episode, Show


SCOPE = "user-library-read user-read-playback-position"
MAX_RETRIES = 5


def now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def make_client() -> spotipy.Spotify:
    load_dotenv()
    return spotipy.Spotify(auth_manager=SpotifyOAuth(scope=SCOPE))


def call_with_retry(fn, *args, **kwargs):
    """
    Call a Spotify API function, retrying on 429 (honoring Retry-After) and 5xx
    (exponential backoff). Re-raises 4xx errors other than 429 immediately.
    """
    for attempt in range(MAX_RETRIES):
        try:
            return fn(*args, **kwargs)
        except SpotifyException as e:
            if e.http_status == 429:
                retry_after = 1
                if e.headers:
                    try:
                        retry_after = int(e.headers.get("Retry-After", "1"))
                    except (TypeError, ValueError):
                        retry_after = 1
                print(f"  rate limited; sleeping {retry_after + 1}s")
                time.sleep(retry_after + 1)
                continue
            if 500 <= e.http_status < 600 and attempt < MAX_RETRIES - 1:
                wait = 2 ** attempt
                print(f"  server error {e.http_status}; retrying in {wait}s")
                time.sleep(wait)
                continue
            raise
    raise RuntimeError(f"Exhausted retries for {getattr(fn, '__name__', fn)}")


def _parse_release_date(value: str | None) -> date | None:
    """Spotify release_date is 'YYYY', 'YYYY-MM', or 'YYYY-MM-DD'."""
    if not value:
        return None
    parts = value.split("-")
    try:
        year = int(parts[0])
        month = int(parts[1]) if len(parts) > 1 else 1
        day = int(parts[2]) if len(parts) > 2 else 1
        return date(year, month, day)
    except (ValueError, IndexError):
        return None


def _images(images: list[dict] | None) -> tuple[str | None, str | None, str | None]:
    """Return (big, medium, small) image URLs from Spotify's image list."""
    if not images:
        return None, None, None
    ordered = sorted(images, key=lambda i: i.get("width") or 0, reverse=True)
    big = ordered[0]["url"]
    small = ordered[-1]["url"]
    medium = ordered[len(ordered) // 2]["url"]
    return big, medium, small


def populate_show(show: Show, data: dict) -> None:
    show.uri = data["uri"]
    show.name = data["name"]
    show.description = data.get("html_description")
    show.total_episodes = data.get("total_episodes")
    show.languages = ",".join(data.get("languages") or []) or None
    show.explicit = data.get("explicit")
    show.spotify_url = (data.get("external_urls") or {}).get("spotify")
    show.media_type = data.get("media_type")
    show.image_url_big, show.image_url_medium, show.image_url_small = _images(data.get("images"))
    show.api_status = "fetched"
    show.last_synced_at = now()


def populate_episode(episode: Episode, data: dict) -> bool:
    """
    Returns True if the API reports new listening activity since the last sync
    (fully-played transitioned or resume position advanced).
    """
    episode.name = data["name"]
    episode.description = data.get("html_description")
    episode.duration_ms = data.get("duration_ms")
    episode.release_date = _parse_release_date(data.get("release_date"))
    episode.languages = ",".join(data.get("languages") or []) or None
    episode.explicit = data.get("explicit")
    episode.spotify_url = (data.get("external_urls") or {}).get("spotify")
    episode.is_playable = data.get("is_playable")
    episode.image_url_big, episode.image_url_medium, episode.image_url_small = _images(data.get("images"))

    rp = data.get("resume_point") or {}
    new_fully_played = bool(rp.get("fully_played"))
    new_resume_pos = rp.get("resume_position_ms")

    became_fully_played = new_fully_played and not episode.is_fully_played
    advanced_resume = (
        new_resume_pos is not None
        and new_resume_pos > (episode.resume_position_ms or 0)
    )

    if new_fully_played:  # never flip fully_played True -> False
        episode.is_fully_played = True
    if new_resume_pos is not None:
        episode.resume_position_ms = new_resume_pos

    episode.api_status = "fetched"
    episode.last_synced_at = now()
    return became_fully_played or advanced_resume


def _initial_sync_done(session) -> bool:
    return session.query(AppState.initial_sync_completed_at).scalar() is not None


def has_listen_evidence(ep_data: dict) -> bool:
    rp = ep_data.get("resume_point") or {}
    return bool(rp.get("fully_played")) or (rp.get("resume_position_ms") or 0) > 0


def auto_finish_shows(session, *, preview=False):
    """
    Mark shows as 'finished' when the user has fully played every known episode.
    Skips shows whose episode count isn't known yet (total_episodes is None/0).
    Skips shows the user already classified ('finished' or 'dropped').
    Returns the number of rows updated, or the matching shows when preview=True.
    """
    q = session.query(Show).filter(
        Show.status.notin_(["finished", "dropped"]),
        Show.total_episodes > 0,
        ~Show.has_more_episodes,
    )
    if preview:
        return q.all()
    return q.update(
        {"status": "finished", "status_changed_at": now()},
        synchronize_session=False,
    )


def auto_pause_stale_shows(session, after_days: int, *, preview=False):
    """
    Move 'active' shows to 'paused' when nothing has been played for `after_days`.
    Skips shows with no last_played_at stamp at all (a NULL means we've never
    observed a play, so 'inactivity' is undefined — respects the point-zero gate).
    Returns the number of rows updated, or the matching shows when preview=True.
    """
    cutoff = now() - timedelta(days=after_days)
    q = session.query(Show).filter(
        Show.status == "active",
        Show.last_played_at.isnot(None),
        Show.last_played_at < cutoff,
    )
    if preview:
        return q.all()
    return q.update(
        {"status": "paused", "status_changed_at": now()},
        synchronize_session=False,
    )


def auto_reactivate_shows(session, *, preview=False):
    """
    Move 'paused' shows back to 'active' when they've been played *since* being
    paused. `status_changed_at` records when the pause happened; a later
    `last_played_at` (stamped by `sync_show_episodes` on observed activity) means
    the user re-engaged. Returns rows updated, or the matching shows when preview=True.
    """
    q = session.query(Show).filter(
        Show.status == "paused",
        Show.status_changed_at.isnot(None),
        Show.last_played_at.isnot(None),
        Show.last_played_at > Show.status_changed_at,
    )
    if preview:
        return q.all()
    return q.update(
        {"status": "active", "status_changed_at": now()},
        synchronize_session=False,
    )


def sync_show_episodes(sp: spotipy.Spotify, session, show: Show, stats: dict) -> None:
    """
    Paginate through a show's episodes and upsert each one into the DB.
    Inserts new episodes only if they have listen evidence.
    Mutates `stats` with `episodes_updated` and `episodes_inserted` counters.
    Sets `show.api_status = "unavailable"` if the show endpoint 404s.
    """
    show_id = show.uri.split(":")[-1]
    gate = _initial_sync_done(session)
    offset = 0
    while True:
        try:
            page = call_with_retry(sp.show_episodes, show_id, limit=50, offset=offset)
        except SpotifyException as e:
            if e.http_status == 404:
                show.api_status = "unavailable"
                return
            raise

        items = page["items"]
        if not items:
            break

        for ep_data in items:
            if ep_data is None:
                continue  # region-restricted; Spotify returns null
            episode = session.query(Episode).filter_by(uri=ep_data["uri"]).first()
            if episode is None:
                if not has_listen_evidence(ep_data):
                    continue  # never-listened episode; we don't track these
                episode = Episode(
                    uri=ep_data["uri"],
                    show_id=show.id,
                    discovered_via="api",
                )
                session.add(episode)
                populate_episode(episode, ep_data)
                if gate:
                    episode.last_played_at = now()
                stats["episodes_inserted"] += 1
            else:
                new_activity = populate_episode(episode, ep_data)
                if gate and new_activity:
                    episode.last_played_at = now()
                stats["episodes_updated"] += 1

        if page["next"] is None:
            break
        offset += 50


def refresh_show(
    sp: spotipy.Spotify,
    session,
    show: Show,
    stats: dict,
    *,
    full: bool,
    escalate_on_new: bool = False,
) -> None:
    """
    Refresh a single already-enriched show.

    `full=True` does a complete pass: fresh metadata + paginate every episode to
    pick up listening progress (the expensive path). `full=False` does a light
    pass: metadata only, plus the cheap `total_episodes`-growth check to flag
    publisher-side new episodes — no episode pagination.

    `escalate_on_new` promotes a light pass to a full one *for this run* when new
    episodes are detected, so a show that's normally only light-refreshed still
    captures any listening that the new episodes triggered.

    Mutates `stats`; does not commit (the caller owns the transaction).
    """
    try:
        show_data = call_with_retry(sp.show, show.uri)
    except SpotifyException as e:
        if e.http_status == 404:
            show.api_status = "unavailable"
            stats["shows_unavailable"] += 1
            return
        raise

    prev_total = show.total_episodes or 0
    new_total = show_data.get("total_episodes") or 0
    grew = new_total > prev_total
    if grew:
        show.has_new_episodes = True
        stats["shows_with_new_episodes"] += 1

    populate_show(show, show_data)

    if full or (grew and escalate_on_new):
        sync_show_episodes(sp, session, show, stats)

    stats["shows_refreshed"] += 1
