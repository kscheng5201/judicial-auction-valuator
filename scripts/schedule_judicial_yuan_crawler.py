"""
Cron entry point: starts the recurring Judicial Yuan crawl schedule (blocking).

  - Historical prices:  once per day at 12:00 (Asia/Taipei)
  - Upcoming auctions:  once per day at 13:00 (Asia/Taipei), after historical finishes

Both jobs run once daily to avoid overloading the judicial server.
Override via JUDICIAL_YUAN_UPCOMING_CRON / JUDICIAL_YUAN_HISTORICAL_CRON
environment variables.

Usage (from repo root):
  python scripts/schedule_judicial_yuan_crawler.py
"""
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

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


def start():
    scheduler = BlockingScheduler(timezone="Asia/Taipei")

    scheduler.add_job(
        run_upcoming,
        CronTrigger.from_crontab(UPCOMING_CRON),
        id="upcoming",
        max_instances=1,
        misfire_grace_time=300,
    )

    scheduler.add_job(
        run_historical,
        CronTrigger.from_crontab(HISTORICAL_CRON),
        id="historical",
        max_instances=1,
        misfire_grace_time=300,
    )

    logger.info("Scheduler starting. upcoming='%s'  historical='%s'",
                UPCOMING_CRON, HISTORICAL_CRON)
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")


if __name__ == "__main__":
    start()
