import argparse

from spotipy.exceptions import SpotifyException

from app.db import SessionLocal
from app.db_models import Episode, Show
from app.spotify import (
    call_with_retry,
    make_client,
    populate_episode,
    populate_show,
    sync_show_episodes,
)


def _resolve_show_uri(sp, session, show: Show) -> bool:
    """
    Find the show's URI by fetching one of its episodes and reading the nested
    `show` field. Tries episodes in turn until one succeeds; marks each failed
    episode as unavailable. Returns True on success.
    """
    episodes = (
        session.query(Episode)
        .filter(Episode.show_id == show.id, Episode.api_status != "unavailable")
        .all()
    )

    for ep in episodes:
        try:
            ep_data = call_with_retry(sp.episode, ep.uri)
        except SpotifyException as e:
            if e.http_status == 404:
                ep.api_status = "unavailable"
                continue
            raise

        nested_show = ep_data.get("show")
        if not nested_show:
            continue  # episode is fine, but can't derive the show from it

        populate_show(show, nested_show)
        populate_episode(ep, ep_data)
        return True

    show.api_status = "unavailable"
    return False


def enrich(session, sp) -> dict:
    stats = {
        "shows_resolved": 0,
        "shows_unavailable": 0,
        "episodes_updated": 0,
        "episodes_inserted": 0,
    }

    shows = session.query(Show).filter(Show.api_status != "unavailable").all()
    for show in shows:
        try:
            if not show.uri:
                print(f"Resolving '{show.name_from_export}'...")
                if not _resolve_show_uri(sp, session, show):
                    stats["shows_unavailable"] += 1
                    session.commit()
                    continue
                stats["shows_resolved"] += 1

            print(f"Enriching episodes for '{show.name}'...")
            sync_show_episodes(sp, session, show, stats)
            session.commit()
        except Exception as e:
            print(f"  ! failed on '{show.name or show.name_from_export}': {e}")
            session.rollback()

    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Enrich shows and episodes in the database via the Spotify API."
    )
    parser.parse_args()

    sp = make_client()
    session = SessionLocal()
    try:
        stats = enrich(session, sp)
    finally:
        session.close()

    print(
        f"\nShows resolved: {stats['shows_resolved']}\n"
        f"Shows unavailable: {stats['shows_unavailable']}\n"
        f"Episodes updated: {stats['episodes_updated']}\n"
        f"Episodes inserted: {stats['episodes_inserted']}"
    )
