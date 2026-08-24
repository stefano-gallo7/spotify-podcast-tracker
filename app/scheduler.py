"""
In-process scheduler for the tiered refresh.

A `BackgroundScheduler` (its own thread pool, off the asyncio event loop) polls
for *due* work on a fixed interval and fires `run_once` when something is due.

Why poll instead of a single daily cron: on a laptop the machine is usually
asleep at any given clock time, and APScheduler *drops* a cron fire it missed
during sleep (default `misfire_grace_time` is 1s — the missed run is discarded,
not run late). A short interval — combined with `misfire_grace_time=None` and
`coalesce=True` — instead re-checks soon after every wake, so a refresh missed
while asleep still happens. Each idle poll is just one cheap `select_due_shows`
query (see `_has_due_work`); the actual rate-limited refresh only runs when a
show crosses its per-status cadence. The run is idempotent and lock-guarded
inside `run_once`.

The first poll fires immediately at startup (`next_run_time`), so a restart
catches up any overdue work without waiting a full interval.

Config (`scheduler_enabled`) is read once at startup; changing it via
`/api/settings` takes effect on the next app restart. `scheduler_run_hour` is
no longer used by the poll (time-of-day is irrelevant once due-ness drives the
refresh); it's kept on `AppState` for compatibility / a possible future
"preferred hour" refinement.

Future, more robust option (survives the app being down entirely): an OS-native
scheduler — macOS `launchd` with `StartCalendarInterval` running
`python -m scripts.scheduled_refresh`, which runs a missed job on next wake.
See TODO.md, "Scheduler — follow-ups".
"""

from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler

from app.db import SessionLocal
from app.db_models import AppState
from app.spotify import now
from scripts.scheduled_refresh import run_once, select_due_shows, setup_logging, _format_stats

# How often to check for due work. The refresh itself is due-gated per show
# (day-scale intervals), so polling hourly does NOT refresh hourly — it just
# bounds catch-up latency after a wake to ~1 interval.
_POLL_INTERVAL_MINUTES = 60

_scheduler: BackgroundScheduler | None = None


def _has_due_work() -> bool:
    session = SessionLocal()
    try:
        config = session.query(AppState).first()
        return bool(config and select_due_shows(session, config, now()))
    finally:
        session.close()


def _job() -> None:
    logger = setup_logging()
    # Cheap gate: on the (common) polls where nothing has come due yet, skip the
    # file lock and Spotify client construction entirely — one DB query and out.
    if not _has_due_work():
        return
    try:
        stats = run_once(logger=logger)
    except Exception as e:  # never let a failed run kill the scheduler thread
        logger.error("Scheduled refresh failed: %s", e)
        return
    logger.info("Done. %s", _format_stats(stats))


def start_scheduler() -> None:
    global _scheduler
    logger = setup_logging()

    session = SessionLocal()
    try:
        config = session.query(AppState).first()
    finally:
        session.close()

    if config is None or not config.scheduler_enabled:
        logger.info("Scheduler disabled; not starting.")
        return

    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(
        _job,
        "interval",
        minutes=_POLL_INTERVAL_MINUTES,
        id="due_poll",
        next_run_time=datetime.now(),  # first poll now (startup catch-up), then every interval
        coalesce=True,                 # collapse polls missed during sleep into one
        misfire_grace_time=None,       # run a poll missed during sleep on wake, don't drop it
    )
    _scheduler.start()
    logger.info("Scheduler started; polling for due work every %d min.", _POLL_INTERVAL_MINUTES)


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
