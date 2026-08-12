"""
Pipeline: crawl upcoming auctions (saletype=1 and saletype=4) for all courts.
Fetches detail pages and PDFs for every listing.
"""
import logging

from .. import config, notify
from ..crawler.session import JudicialSession
from ..crawler.query import fetch_all_pages, upcoming_date_range
from ..crawler.detail import fetch_detail
from ..crawler.pdf import fetch_and_store_pdf
from .upsert import (
    map_record, upsert_auction, upsert_detail,
    log_run_start, log_run_finish, get_last_success_finish,
)

logger = logging.getLogger(__name__)


def run_upcoming():
    since = get_last_success_finish("upcoming")
    date_from, date_to = upcoming_date_range(since=since)
    logger.info("Upcoming pipeline: %s → %s (last success: %s)",
                date_from, date_to, since)

    session = JudicialSession()
    try:
        session.refresh_csrf()
    except Exception as exc:
        logger.exception("Upcoming pipeline aborted: could not establish session")
        run_id = log_run_start("upcoming", None, None, None, date_from, date_to)
        log_run_finish(run_id, 0, 0, 0, status="error", error=str(exc))
        notify.send_alert(
            "Judicial Yuan crawler: upcoming pipeline failed",
            f"Could not establish a session (likely no internet): {exc}",
        )
        return

    total_found = total_new = total_updated = 0

    for court_code, court_name in config.COURTS:
        for sale_type in config.SALE_TYPE_UPCOMING:
            for prop_type in config.PROP_TYPES:

                run_id = log_run_start(
                    "upcoming", court_code, sale_type, prop_type,
                    date_from, date_to,
                )
                found = new_cnt = upd_cnt = 0

                try:
                    for page_records in fetch_all_pages(
                        session, court_code, court_name,
                        sale_type, prop_type, date_from, date_to,
                    ):
                        for raw in page_records:
                            found += 1
                            row = map_record(raw, court_code, court_name,
                                             sale_type, prop_type)
                            auction_id = upsert_auction(row)
                            is_new = (auction_id > 0)  # heuristic via lastrowid
                            if is_new:
                                new_cnt += 1
                            else:
                                upd_cnt += 1

                            # Fetch detail + PDF for every record
                            # para  = base64 key for the detail page
                            # file_name = PDF path (e.g. /tpd/115.../xxx.pdf)
                            para      = row.get("para")
                            file_name = row.get("file_name")
                            if para or file_name:
                                detail = fetch_detail(session, para, filenm=file_name)
                                pdf_result = {"local_path": None,
                                              "text": "", "structured_json": None}
                                if detail.get("pdf_url"):
                                    pdf_result = fetch_and_store_pdf(
                                        session,
                                        detail["pdf_url"],
                                        court_code,
                                        file_name or para,
                                    )
                                upsert_detail(
                                    auction_id=auction_id,
                                    pdf_url=detail.get("pdf_url"),
                                    pdf_local_path=pdf_result["local_path"],
                                    pdf_text=pdf_result["text"],
                                    pdf_structured=pdf_result["structured_json"],
                                    detail_raw=detail.get("raw_json"),
                                )

                    log_run_finish(run_id, found, new_cnt, upd_cnt)

                except Exception as exc:
                    logger.exception(
                        "Upcoming run error court=%s sale=%s prop=%s",
                        court_code, sale_type, prop_type,
                    )
                    log_run_finish(run_id, found, new_cnt, upd_cnt,
                                   status="error", error=str(exc))

                total_found   += found
                total_new     += new_cnt
                total_updated += upd_cnt

    logger.info(
        "Upcoming pipeline done. found=%d new=%d updated=%d",
        total_found, total_new, total_updated,
    )
