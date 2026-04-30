"""
Shared helpers for talking to the Spotify Web API.

Used by both the enrichment script (initial fill-in after import) and the
refresh script (periodic re-sync of metadata + listening progress).
"""

import time
from datetime import date, datetime, timezone

import spotipy
from dotenv import load_dotenv
from spotipy.exceptions import SpotifyException
from spotipy.oauth2 import SpotifyOAuth

from app.db_models import Episode, Show


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


def populate_episode(episode: Episode, data: dict) -> None:
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
    if rp.get("fully_played"):  # never flip fully_played True -> False
        episode.is_fully_played = True
    if rp.get("resume_position_ms") is not None:
        episode.resume_position_ms = rp["resume_position_ms"]

    episode.api_status = "fetched"
    episode.last_synced_at = now()


def has_listen_evidence(ep_data: dict) -> bool:
    rp = ep_data.get("resume_point") or {}
    return bool(rp.get("fully_played")) or (rp.get("resume_position_ms") or 0) > 0


def auto_finish_shows(session) -> int:
    """
    Mark shows as 'finished' when the user has fully played every known episode.
    Skips shows whose episode count isn't known yet (total_episodes is None/0).
    Skips shows the user already classified ('finished' or 'dropped').
    Returns the number of rows updated.
    """
    return (
        session.query(Show)
        .filter(
            Show.status.notin_(["finished", "dropped"]),
            Show.total_episodes > 0,
            ~Show.has_more_episodes,
        )
        .update(
            {"status": "finished", "status_changed_at": now()},
            synchronize_session=False,
        )
    )


def sync_show_episodes(sp: spotipy.Spotify, session, show: Show, stats: dict) -> None:
    """
    Paginate through a show's episodes and upsert each one into the DB.
    Inserts new episodes only if they have listen evidence.
    Mutates `stats` with `episodes_updated` and `episodes_inserted` counters.
    Sets `show.api_status = "unavailable"` if the show endpoint 404s.
    """
    show_id = show.uri.split(":")[-1]
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
                stats["episodes_inserted"] += 1
            else:
                populate_episode(episode, ep_data)
                stats["episodes_updated"] += 1

        if page["next"] is None:
            break
        offset += 50
