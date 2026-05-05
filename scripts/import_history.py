import argparse
import json
from datetime import datetime

from app.db import SessionLocal
from app.db_models import Episode, Show


def _normalize(name: str) -> str:
    return name.strip().casefold()


def _parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts.removesuffix("Z"))


def import_history(history_path: str, session) -> dict[str, int]:
    """
    Load the parsed podcast history JSON and upsert into shows + episodes.

    Idempotent: re-running with the same file is a no-op; re-running with a
    superset (new history files merged in) updates listening info where the
    new play event is later or longer.
    """
    with open(history_path, encoding="utf-8") as f:
        entries = json.load(f)

    show_cache: dict[str, Show] = {
        _normalize(s.name): s for s in session.query(Show).all()
    }
    episode_cache: dict[str, Episode] = {
        e.uri: e for e in session.query(Episode).all()
    }

    stats = {
        "shows_created": 0,
        "episodes_created": 0,
        "episodes_updated": 0,
        "episodes_unchanged": 0,
    }

    for entry in entries:
        show_name = entry["show_name"]
        show = _get_or_create_show(session, show_name, show_cache, stats)

        uri = entry["spotify_episode_uri"]
        episode = episode_cache.get(uri)
        if episode is None:
            episode = _create_episode(entry, show)
            session.add(episode)
            episode_cache[uri] = episode
            stats["episodes_created"] += 1
        else:
            if _update_episode(episode, entry):
                stats["episodes_updated"] += 1
            else:
                stats["episodes_unchanged"] += 1

    session.commit()
    return stats


def _get_or_create_show(
    session, show_name: str, cache: dict[str, Show], stats: dict[str, int]
) -> Show:
    key = _normalize(show_name)
    show = cache.get(key)
    if show is not None:
        if show.name_from_export is None:
            show.name_from_export = show_name
        return show

    show = Show(name=show_name, name_from_export=show_name, api_status="pending")
    session.add(show)
    session.flush()  # populate show.id for the FK
    cache[key] = show
    stats["shows_created"] += 1
    return show


def _create_episode(entry: dict, show: Show) -> Episode:
    return Episode(
        uri=entry["spotify_episode_uri"],
        show_id=show.id,
        name=entry["episode_name"],
        name_from_export=entry["episode_name"],
        last_played_at=_parse_ts(entry["last_listened_at"]),
        ms_played=entry["ms_played"],
        play_count=entry["play_count"],
        is_fully_played=entry["is_fully_played"],
        connection_country=entry.get("connection_country"),
        discovered_via="export",
        api_status="pending",
    )


def _update_episode(episode: Episode, entry: dict) -> bool:
    listened_at = _parse_ts(entry["last_listened_at"])
    ms_played = entry["ms_played"]
    play_count = entry["play_count"]
    is_fully_played = entry["is_fully_played"]
    changed = False

    if episode.last_played_at is None or listened_at > episode.last_played_at:
        episode.last_played_at = listened_at
        episode.connection_country = entry.get("connection_country")
        changed = True

    if episode.ms_played is None or ms_played > episode.ms_played:
        episode.ms_played = ms_played
        changed = True

    if episode.play_count is None or play_count > episode.play_count:
        episode.play_count = play_count
        changed = True

    if is_fully_played and not episode.is_fully_played:
        episode.is_fully_played = True
        changed = True

    if episode.name_from_export is None:
        episode.name_from_export = entry["episode_name"]
        changed = True

    return changed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Import parsed Spotify podcast history into the database."
    )
    parser.add_argument(
        "--history",
        default="data/podcast_history.json",
        metavar="PATH",
        help="Path to the parsed history JSON (default: data/podcast_history.json)",
    )
    args = parser.parse_args()

    session = SessionLocal()
    try:
        stats = import_history(args.history, session)
    finally:
        session.close()

    print(
        f"Shows created: {stats['shows_created']}\n"
        f"Episodes created: {stats['episodes_created']}\n"
        f"Episodes updated: {stats['episodes_updated']}\n"
        f"Episodes unchanged: {stats['episodes_unchanged']}"
    )
