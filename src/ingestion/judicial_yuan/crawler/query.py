"""
Builds POST payloads and paginates through QUERY.htm results.
"""
from datetime import date, timedelta
from typing import Iterator, List, Dict, Any, Optional
import logging

from .. import config
from .session import JudicialSession

logger = logging.getLogger(__name__)


def _to_roc_date(d: date) -> str:
    """Convert a Python date to Taiwan ROC 7-digit format: YYYMMDD."""
    roc_year = d.year - 1911
    return f"{roc_year:03d}{d.month:02d}{d.day:02d}"


def _build_payload(
    court_code: str,
    court_name: str,
    sale_type: str,
    prop_type: str,
    date_from: date,
    date_to: date,
    page_no: int = 1,
) -> Dict[str, Any]:
    return {
        "court":          court_code,
        "crtnm":          court_name,
        "county":         "",
        "town":           "",
        "sec":            "",
        "proptype":       prop_type,
        "saletype":       sale_type,
        "saledate1":      _to_roc_date(date_from),
        "saledate2":      _to_roc_date(date_to),
        "saleno":         "",
        "keyword":        "",
        "crmyy":          "",
        "crmid":          "",
        "crmno":          "",
        "dpt":            "",
        "minprice1":      "",
        "minprice2":      "",
        "area1":          "",
        "area2":          "",
        "debtor":         "",
        "ttitle":         "",
        "rrange":         "",
        "checkyn":        "",
        "emptyyn":        "",
        "comm_yn":        "",
        "stopitem":       "",
        "gov":            "",
        "sorted_column":  "A.SALEDATE,A.CRMYY,A.CRMID,A.CRMNO,A.SALENO,A.ROWID",
        "sorted_type":    "ASC",
        "_ORDER_BY":      "",
        "pageNum":        str(page_no),
        "pageSize":       str(config.PAGE_SIZE),
    }


def fetch_all_pages(
    session: JudicialSession,
    court_code: str,
    court_name: str,
    sale_type: str,
    prop_type: str,
    date_from: date,
    date_to: date,
) -> Iterator[List[Dict]]:
    """
    Yields lists of raw record dicts, one list per page.
    Handles pagination automatically.
    """
    page_no = 1
    total_pages = None

    while True:
        payload = _build_payload(
            court_code, court_name, sale_type, prop_type,
            date_from, date_to, page_no,
        )

        try:
            resp = session.post_query(payload)
        except Exception as exc:
            logger.error(
                "Query failed court=%s sale_type=%s prop_type=%s page=%d: %s",
                court_code, sale_type, prop_type, page_no, exc,
            )
            break

        if resp.get("status") != "SUCCESS":
            msg = resp.get("messageText", "")
            # "不合法的查詢" just means no results for this combo — not a real error
            if "不合法" not in msg:
                logger.warning(
                    "Non-success for court=%s sale_type=%s prop_type=%s: %s",
                    court_code, sale_type, prop_type, msg,
                )
            break

        records = resp.get("data") or []
        if not records:
            break

        yield records

        # Parse pagination on first page
        # API returns pageInfo.totalNum (not totalRecord/total)
        if total_pages is None:
            page_info = resp.get("pageInfo") or {}
            total_records = int(
                page_info.get("totalNum") or
                page_info.get("totalRecord") or
                page_info.get("total") or 0
            )
            page_size = int(page_info.get("pageSize") or config.PAGE_SIZE)
            if total_records and page_size:
                total_pages = (total_records + page_size - 1) // page_size
            else:
                total_pages = 1

        if page_no >= total_pages:
            break

        page_no += 1
        # Refresh CSRF every 50 pages to avoid token expiry
        if page_no % 50 == 0:
            try:
                session.refresh_csrf()
            except Exception:
                pass


def upcoming_date_range(since: Optional[date] = None) -> tuple:
    """
    since: date of the last successful run of this pipeline, if any.
    If the default window's start is later than `since` — i.e. the
    pipeline failed or didn't run for longer than the window normally
    covers — widen date_from back to `since` so nothing in that gap is
    missed on this run.
    """
    today = date.today()
    date_from = today
    if since and since < date_from:
        date_from = since
    return date_from, today + timedelta(days=config.UPCOMING_DAYS_AHEAD)


def historical_date_range(since: Optional[date] = None) -> tuple:
    """See upcoming_date_range for what `since` does."""
    today = date.today()
    date_from = today - timedelta(days=config.HISTORICAL_DAYS_BACK)
    if since and since < date_from:
        date_from = since
    return date_from, today
