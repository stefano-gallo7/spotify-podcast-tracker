"""
Tiered, status-aware refresh for scheduled (e.g. nightly) runs.

Unlike `refresh_from_api.py` (which fully refreshes every show on every run),
this picks only the shows that are *due* based on per-status cadence, and uses a
cheap metadata-only "light" pass for finished shows. It then applies the
automatic status transitions (finish / pause / reactivate). All behavior is
driven by the config columns on the `AppState` singleton.

Designed to be both a CLI (`python -m scripts.scheduled_refresh`) and a
programmatic entry point for the in-process scheduler (`run_once`).

The run is idempotent: firing it more often than the cadence is harmless
(nothing comes due), firing it less often just delays a tier.
"""

import argparse
import logging
import os
from contextlib import contextmanager, nullcontext
from datetime import timedelta
from logging.handlers import RotatingFileHandler

from app.db import SessionLocal
from app.db_models import AppState, Show
from app.spotify import (
    auto_finish_shows,
    auto_pause_stale_shows,
    auto_reactivate_shows,
    make_client,
    now,
    refresh_show,
)

LOG_PATH = "data/refresh.log"
LOCK_PATH = "data/.refresh.lock"

# A show's "due" check compares now - last_synced_at against its interval. We
# subtract this slack so a run that starts a little late or takes a while (the
# Spotify pass is rate-limited and can run for many minutes) doesn't push the
# next day's run just past the boundary and silently skip a tier.
_DUE_SLACK = timedelta(hours=12)


def _mode_for(status: str) -> tuple[bool, bool]:
    """(full, escalate_on_new) for a status. active/paused → full refresh;
    finished → light refresh that escalates to full only if new episodes appear."""
    if status in ("active", "paused"):
        return True, False
    if status == "finished":
        return False, True
    return False, False  # unreachable for selected shows; defensive default


def _interval_for(status: str, config: AppState) -> int | None:
    """Days between refreshes for a status, or None to skip it entirely."""
    return {
        "active": config.refresh_active_interval_days,
        "paused": config.refresh_paused_interval_days,
        "finished": config.refresh_finished_interval_days,
    }.get(status)


def select_due_shows(session, config: AppState, at, *, force: bool = False) -> list:
    """Return [(show, full, escalate_on_new)] for shows due to refresh at `at`."""
    shows = (
        session.query(Show)
        .filter(
            Show.api_status == "fetched",
            Show.uri.isnot(None),
            Show.status.notin_(["dropped"]),
        )
        .all()
    )

    due = []
    for show in shows:
        interval = _interval_for(show.status, config)
        if interval is None:
            continue
        is_due = (
            force
            or show.last_synced_at is None
            or (at - show.last_synced_at) >= timedelta(days=interval) - _DUE_SLACK
        )
        if is_due:
            full, escalate = _mode_for(show.status)
            due.append((show, full, escalate))
    return due


def _log_transition_group(logger, verb: str, shows: list, enabled: bool, note: str = "") -> None:
    if not enabled:
        logger.info("  would %s: disabled", verb)
        return
    suffix = f" ({note})" if note else ""
    logger.info("  would %s %d show(s)%s", verb, len(shows), suffix)
    for show in shows:
        logger.info("    - %s", show.name)


def _log_transition_preview(session, config: AppState, logger) -> None:
    """List the shows each transition would affect, in live order: finish runs
    first, so a finished show can't also pause/reactivate — exclude its ids."""
    finish = auto_finish_shows(session, preview=True) if config.auto_finish_enabled else []
    finish_ids = {s.id for s in finish}
    pause = (
        [s for s in auto_pause_stale_shows(session, config.auto_pause_after_days, preview=True)
         if s.id not in finish_ids]
        if config.auto_pause_enabled else []
    )
    reactivate = (
        [s for s in auto_reactivate_shows(session, preview=True) if s.id not in finish_ids]
        if config.auto_reactivate_enabled else []
    )

    _log_transition_group(logger, "finish", finish, config.auto_finish_enabled)
    _log_transition_group(logger, "pause", pause, config.auto_pause_enabled,
                          note=f"idle > {config.auto_pause_after_days}d")
    _log_transition_group(logger, "reactivate", reactivate, config.auto_reactivate_enabled)


def _empty_stats() -> dict:
    return {
        "shows_refreshed": 0,
        "shows_unavailable": 0,
        "shows_with_new_episodes": 0,
        "shows_finished": 0,
        "shows_paused": 0,
        "shows_reactivated": 0,
        "episodes_updated": 0,
        "episodes_inserted": 0,
    }


def _run(session, sp, config: AppState, *, dry_run: bool, force: bool, logger) -> dict:
    stats = _empty_stats()
    at = now()
    due = select_due_shows(session, config, at, force=force)
    logger.info("%d show(s) due for refresh", len(due))

    if dry_run:
        for show, full, escalate in due:
            mode = "full" if full else "light"
            tail = " (escalates on new episodes)" if escalate else ""
            logger.info("  would refresh [%s] %s — %s%s", show.status, show.name, mode, tail)
        logger.info("transitions below reflect current data (refresh is skipped in dry-run):")
        _log_transition_preview(session, config, logger)
        return stats

    for show, full, escalate in due:
        try:
            logger.info("Refreshing '%s' (%s)...", show.name, "full" if full else "light")
            refresh_show(sp, session, show, stats, full=full, escalate_on_new=escalate)
            session.commit()
        except Exception as e:  # one bad show shouldn't abort the whole run
            logger.warning("  ! failed on '%s': %s", show.name, e)
            session.rollback()

    # Automatic status transitions, in order: a caught-up show finishes; a long-idle
    # show pauses; a paused show played since pausing reactivates.
    if config.auto_finish_enabled:
        stats["shows_finished"] = auto_finish_shows(session)
    if config.auto_pause_enabled:
        stats["shows_paused"] = auto_pause_stale_shows(session, config.auto_pause_after_days)
    if config.auto_reactivate_enabled:
        stats["shows_reactivated"] = auto_reactivate_shows(session)
    session.commit()
    return stats


def run_once(*, dry_run: bool = False, force: bool = False, logger=None) -> dict:
    """Open a session (+ Spotify client unless dry-run) and run one tiered refresh.

    Programmatic entry point used by both the CLI and the in-process scheduler.
    """
    logger = logger or setup_logging()
    # Real runs take the lock (rate-limited, long, mutating); dry-run is read-only.
    lock = nullcontext() if dry_run else _file_lock(LOCK_PATH)
    with lock:
        session = SessionLocal()
        try:
            config = session.query(AppState).first()
            if config is None:
                raise RuntimeError("AppState row missing — run `python -m scripts.init_db` first.")
            sp = None if dry_run else make_client()
            return _run(session, sp, config, dry_run=dry_run, force=force, logger=logger)
        finally:
            session.close()


@contextmanager
def _file_lock(path: str):
    """Refuse to start if a run is already in progress (rate-limited runs can be
    long; overlapping runs would double the API load and race on commits)."""
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise RuntimeError(
            f"A refresh appears to be running (lock file '{path}' exists). "
            "Delete it if you're sure no run is active."
        )
    try:
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        yield
    finally:
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("scheduled_refresh")
    if logger.handlers:  # idempotent: scheduler may call this repeatedly
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%Y-%m-%d %H:%M:%S")
    file_handler = RotatingFileHandler(LOG_PATH, maxBytes=1_000_000, backupCount=3)
    file_handler.setFormatter(fmt)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(fmt)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger


def _format_stats(stats: dict) -> str:
    return ", ".join(f"{k}={v}" for k, v in stats.items())


def main():
    parser = argparse.ArgumentParser(
        description="Tiered, status-aware Spotify refresh for scheduled runs."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report which shows are due and which transitions would run, without writing.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Ignore per-status intervals and refresh every eligible show.",
    )
    args = parser.parse_args()

    logger = setup_logging()
    try:
        stats = run_once(dry_run=args.dry_run, force=args.force, logger=logger)
    except Exception as e:
        logger.error("Refresh run failed: %s", e)
        raise SystemExit(1)

    logger.info("Done. %s", _format_stats(stats))


if __name__ == "__main__":
    main()
