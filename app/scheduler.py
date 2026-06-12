"""
In-process daily scheduler for the tiered refresh.

A `BackgroundScheduler` (its own thread pool, off the asyncio event loop) fires
`run_once` once a day at the configured hour. On startup we also run a one-off
catch-up *if* there's overdue work, so a refresh missed while the app was down
(e.g. the machine was asleep at the scheduled hour) still happens. The run is
idempotent and lock-guarded inside `run_once`, so catch-up and the daily fire
can never overlap.

Config (`scheduler_enabled`, `scheduler_run_hour`) is read once at startup;
changing it via `/api/settings` takes effect on the next app restart.
"""

from apscheduler.schedulers.background import BackgroundScheduler

from app.db import SessionLocal
from app.db_models import AppState
from app.spotify import now
from scripts.scheduled_refresh import run_once, select_due_shows, setup_logging, _format_stats

_scheduler: BackgroundScheduler | None = None


def _job() -> None:
    logger = setup_logging()
    try:
        stats = run_once(logger=logger)
    except Exception as e:  # never let a failed run kill the scheduler thread
        logger.error("Scheduled refresh failed: %s", e)

    logger.info("Done. %s", _format_stats(stats))


def _has_due_work() -> bool:
    session = SessionLocal()
    try:
        config = session.query(AppState).first()
        return bool(config and select_due_shows(session, config, now()))
    finally:
        session.close()


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
    _scheduler.add_job(_job, "cron", hour=config.scheduler_run_hour, minute=0, id="daily_refresh")
    _scheduler.start()
    logger.info("Scheduler started; daily refresh at %02d:00 local time.", config.scheduler_run_hour)

    if _has_due_work():
        logger.info("Overdue work detected on startup; running catch-up refresh.")
        _scheduler.add_job(_job, id="startup_catchup")  # one-off, runs immediately


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
