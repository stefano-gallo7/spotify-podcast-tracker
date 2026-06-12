import argparse

from app.db import SessionLocal
from app.db_models import Show
from app.spotify import auto_finish_shows, make_client, refresh_show


def refresh(session, sp) -> dict:
    """
    Re-sync shows that are already enriched: pull fresh metadata, detect
    publisher-side new episodes via total_episodes growth, and update
    listening progress for known episodes. Every show gets a full refresh;
    `scheduled_refresh.py` is the tiered, status-aware variant.
    """
    stats = {
        "shows_refreshed": 0,
        "shows_unavailable": 0,
        "shows_with_new_episodes": 0,
        "shows_finished": 0,
        "episodes_updated": 0,
        "episodes_inserted": 0,
    }

    shows = (
        session.query(Show)
        .filter(
            Show.api_status == "fetched",
            Show.uri.isnot(None),
            Show.status.notin_(["dropped"]),
        )
        .all()
    )

    for show in shows:
        try:
            print(f"Refreshing '{show.name}'...")
            refresh_show(sp, session, show, stats, full=True)
            session.commit()
        except Exception as e:
            print(f"  ! failed on '{show.name}': {e}")
            session.rollback()

    stats["shows_finished"] = auto_finish_shows(session)
    session.commit()
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Refresh show metadata and episode listening data via the Spotify API."
    )
    parser.parse_args()

    sp = make_client()
    session = SessionLocal()
    try:
        stats = refresh(session, sp)
    finally:
        session.close()

    print(
        f"\nShows refreshed: {stats['shows_refreshed']}\n"
        f"Shows unavailable: {stats['shows_unavailable']}\n"
        f"Shows with new episodes: {stats['shows_with_new_episodes']}\n"
        f"Shows finished: {stats['shows_finished']}\n"
        f"Episodes updated: {stats['episodes_updated']}\n"
        f"Episodes inserted: {stats['episodes_inserted']}"
    )
