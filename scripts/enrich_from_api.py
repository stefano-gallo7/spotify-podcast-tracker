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


def _merge_show(session, source: Show, target: Show) -> None:
    """
    Merge `source` into `target` (which already holds the canonical URI):
    re-parent episodes, preserve the older export name(s) in
    `target.name_from_export`, delete source.

    name_from_export rules (target.name is the current API name):
    - If target's export name matches the current name, swap in source's older
      name (target was the "current name" row).
    - If source's export name matches the current name, keep target's older
      name (target was already the "old name" row).
    - Otherwise (show renamed more than once), append source's name to
      target's so every historical export name is preserved.
    """
    session.query(Episode).filter(Episode.show_id == source.id).update(
        {"show_id": target.id}, synchronize_session="fetch"
    )
    if source.name_from_export:
        if target.name_from_export is None or target.name_from_export == target.name:
            target.name_from_export = source.name_from_export
        elif source.name_from_export != target.name:
            target.name_from_export = (
                f"{target.name_from_export}, {source.name_from_export}"
            )
    session.delete(source)


def _resolve_show_uri(sp, session, show: Show) -> Show | None:
    """
    Find the show's URI by fetching one of its episodes and reading the nested
    `show` field. Tries episodes in turn until one succeeds; marks each failed
    episode as unavailable.

    Returns the canonical Show on success: the same `show` after population,
    or a different existing row if `show` turned out to be a renamed-show
    duplicate that got merged into it. Returns None if no episode resolved.
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

        existing = (
            session.query(Show)
            .filter(Show.uri == nested_show["uri"], Show.id != show.id)
            .first()
        )
        if existing is not None:
            _merge_show(session, source=show, target=existing)
            return existing

        populate_show(show, nested_show)
        populate_episode(ep, ep_data)
        return show

    show.api_status = "unavailable"
    return None


def enrich(session, sp) -> dict:
    stats = {
        "shows_resolved": 0,
        "shows_merged": 0,
        "shows_unavailable": 0,
        "episodes_updated": 0,
        "episodes_inserted": 0,
    }

    shows = session.query(Show).filter(Show.api_status != "unavailable").all()
    for show in shows:
        try:
            if not show.uri:
                print(f"Resolving '{show.name_from_export}'...")
                resolved = _resolve_show_uri(sp, session, show)
                if resolved is None:
                    stats["shows_unavailable"] += 1
                    session.commit()
                    continue
                if resolved is not show:
                    print(f"  merged into '{resolved.name}'; re-syncing episodes")
                    stats["shows_merged"] += 1
                    sync_show_episodes(sp, session, resolved, stats)
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
        f"Shows merged: {stats['shows_merged']}\n"
        f"Shows unavailable: {stats['shows_unavailable']}\n"
        f"Episodes updated: {stats['episodes_updated']}\n"
        f"Episodes inserted: {stats['episodes_inserted']}"
    )
