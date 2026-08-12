"""
Cron entry point: starts the recurring Judicial Yuan crawl schedule (blocking).

  - Historical prices:  once per day at 12:00 (Asia/Taipei)
  - Upcoming auctions:  once per day at 13:00 (Asia/Taipei), after historical finishes

Both jobs run once daily to avoid overloading the judicial server.
Override via JUDICIAL_YUAN_UPCOMING_CRON / JUDICIAL_YUAN_HISTORICAL_CRON
environment variables.

Each pipeline already guards its own network/session setup and logs a
failure row + alert instead of crashing (see pipeline/upcoming.py,
pipeline/historical.py) — the job-error listener below is a backstop
for anything unexpected that still escapes that (e.g. the database
itself being unreachable), so a crash is never silent.

misfire_grace_time is intentionally generous (default 6h): if this
desktop is asleep or offline at the scheduled fire time, APScheduler
should still run the job once it wakes up within that window rather
than skipping the day entirely. coalesce=True collapses multiple
missed firings into a single catch-up run.

Usage (from repo root):
  python scripts/schedule_judicial_yuan_crawler.py
"""
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apscheduler.events import EVENT_JOB_ERROR
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from src.ingestion.judicial_yuan import notify
from src.ingestion.judicial_yuan.pipeline.upcoming import run_upcoming
from src.ingestion.judicial_yuan.pipeline.historical import run_historical

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

UPCOMING_CRON   = os.getenv("JUDICIAL_YUAN_UPCOMING_CRON",   "0 13 * * *")  # daily 13:00 Asia/Taipei
HISTORICAL_CRON = os.getenv("JUDICIAL_YUAN_HISTORICAL_CRON", "0 12 * * *")  # daily 12:00 Asia/Taipei
MISFIRE_GRACE_SECONDS = int(os.getenv("JUDICIAL_YUAN_MISFIRE_GRACE_SECONDS", str(6 * 3600)))


def _on_job_error(event):
    notify.send_alert(
        f"Judicial Yuan crawler: scheduled job '{event.job_id}' crashed",
        str(event.exception),
    )


def start():
    scheduler = BlockingScheduler(timezone="Asia/Taipei")
    scheduler.add_listener(_on_job_error, EVENT_JOB_ERROR)

    scheduler.add_job(
        run_upcoming,
        CronTrigger.from_crontab(UPCOMING_CRON),
        id="upcoming",
        max_instances=1,
        misfire_grace_time=MISFIRE_GRACE_SECONDS,
        coalesce=True,
    )

    scheduler.add_job(
        run_historical,
        CronTrigger.from_crontab(HISTORICAL_CRON),
        id="historical",
        max_instances=1,
        misfire_grace_time=MISFIRE_GRACE_SECONDS,
        coalesce=True,
    )

    logger.info(
        "Scheduler starting. upcoming='%s'  historical='%s'  misfire_grace=%ds",
        UPCOMING_CRON, HISTORICAL_CRON, MISFIRE_GRACE_SECONDS,
    )
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")


if __name__ == "__main__":
    start()
