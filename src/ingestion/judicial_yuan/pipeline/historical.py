"""
Pipeline: crawl 拍定價格 (saletype=5, completed auctions) for all courts.
Goes back HISTORICAL_DAYS_BACK days (default: 365 = 1 year).
Does NOT fetch PDFs — just stores the hammer price records.
"""
import logging

from .. import config
from ..crawler.session import JudicialSession
from ..crawler.query import fetch_all_pages, historical_date_range
from .upsert import (
    map_record, upsert_auction,
    log_run_start, log_run_finish,
)

logger = logging.getLogger(__name__)


def run_historical():
    date_from, date_to = historical_date_range()
    logger.info("Historical pipeline: %s → %s", date_from, date_to)

    session = JudicialSession()
    session.refresh_csrf()

    total_found = total_new = total_updated = 0

    for court_code, court_name in config.COURTS:
        for prop_type in config.PROP_TYPES:

            run_id = log_run_start(
                "historical", court_code, "5", prop_type,
                date_from, date_to,
            )
            found = new_cnt = upd_cnt = 0

            try:
                for page_records in fetch_all_pages(
                    session, court_code, court_name,
                    "5", prop_type, date_from, date_to,
                ):
                    for raw in page_records:
                        found += 1
                        row = map_record(raw, court_code, court_name, "5", prop_type)
                        upsert_auction(row)
                        new_cnt += 1  # simplification; upsert handles real dedup

                log_run_finish(run_id, found, new_cnt, upd_cnt)

            except Exception as exc:
                logger.exception(
                    "Historical run error court=%s prop=%s",
                    court_code, prop_type,
                )
                log_run_finish(run_id, found, new_cnt, upd_cnt,
                               status="error", error=str(exc))

            total_found   += found
            total_new     += new_cnt
            total_updated += upd_cnt

    logger.info(
        "Historical pipeline done. found=%d new=%d updated=%d",
        total_found, total_new, total_updated,
    )
