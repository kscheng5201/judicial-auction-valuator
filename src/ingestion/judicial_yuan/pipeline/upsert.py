"""
Database upsert helpers for auctions and auction_details.
"""
import json
import logging
from datetime import date
from typing import Dict, Any, Optional

from ..db.connection import get_cursor

logger = logging.getLogger(__name__)


def get_last_success_finish(run_type: str) -> Optional[date]:
    """
    Date the given run_type ('upcoming' / 'historical') last completed
    successfully, across all court/sale-type/prop-type combinations.
    None if it has never succeeded (e.g. first run, or fresh database).

    Used to widen the pipeline's default query window when the last
    run failed or was skipped entirely, so the gap gets covered on the
    next successful run rather than silently lost.
    """
    with get_cursor() as cur:
        cur.execute(
            "SELECT MAX(finished_at) AS last_success "
            "FROM crawler_runs WHERE run_type=%s AND status='success'",
            (run_type,),
        )
        row = cur.fetchone()
        finished_at = row["last_success"] if row else None
        return finished_at.date() if finished_at else None


def _roc_to_iso(roc_date_str: Optional[str]) -> Optional[str]:
    """Convert YYYMMDD (ROC) → YYYY-MM-DD (Gregorian). Returns None on failure.

    民國 year + 1911 = Gregorian year  (e.g. 民國 99 年 → 2010)
    """
    if not roc_date_str or len(roc_date_str) != 7:
        return None
    try:
        roc_year = int(roc_date_str[:3])
        month = int(roc_date_str[3:5])
        day = int(roc_date_str[5:7])
        year = roc_year + 1911
        return f"{year:04d}-{month:02d}-{day:02d}"
    except (ValueError, TypeError):
        return None


def _roc_year_to_gregorian(val) -> int:
    """Convert a bare 民國 year number to Gregorian year.

    e.g. 99 → 2010,  115 → 2026.  Returns 0 when the value is absent/invalid.
    """
    try:
        roc = int(val)
        return roc + 1911 if roc > 0 else 0
    except (ValueError, TypeError):
        return 0


def _str_price(val) -> Optional[int]:
    if val is None or val == "":
        return None
    try:
        return int(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def _str_float(val) -> Optional[float]:
    if val is None or val == "":
        return None
    try:
        return float(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def _yn(val) -> Optional[str]:
    """Normalise various truthy values to 'Y'/'N'/None."""
    if val is None or val == "":
        return None
    s = str(val).upper().strip()
    if s in ("Y", "YES", "是", "1", "TRUE"):
        return "Y"
    if s in ("N", "NO", "否", "0", "FALSE"):
        return "N"
    return None


def map_record(raw: Dict[str, Any], court_code: str, court_name: str,
               sale_type: str, prop_type: str) -> Dict[str, Any]:
    """
    Maps a raw JSON record from QUERY.htm to our auctions table columns.
    All known field name variants are handled; the full raw dict is stored as-is.
    """
    g = raw.get

    sale_date_roc = g("saledate") or g("SALEDATE") or g("sale_date") or ""
    upload_dt     = g("upload_dt") or g("UPLOAD_DT") or ""
    upload_tm     = g("upload_tm") or g("UPLOAD_TM") or ""

    return {
        "court_code":      court_code,
        "court_name":      court_name,
        "case_year":       _roc_year_to_gregorian(g("crmyy") or g("CRMYY")),
        "case_type":       str(g("crmid") or g("CRMID") or ""),
        "case_no":         str(g("crmno") or g("CRMNO") or ""),
        "case_division":   str(g("dpt")   or g("DPT")   or ""),
        "auction_round":   int(g("saleno") or g("SALENO") or 1),
        "file_name":       g("filenm") or g("FILENM") or None,   # PDF path, e.g. /tpd/115.../xxx.pdf
        "para":            g("para")   or g("PARA")   or None,   # base64 key for detail page
        "sale_type":       int(sale_type),
        "prop_type":       prop_type,
        "county_no":       g("countyno") or g("COUNTYNO") or None,
        "county_name":     g("county")   or g("COUNTY")   or None,
        "district":        (g("ctmd") or g("CTMD") or
                            g("hsimun") or g("HSIMUN") or None),
        "section":         g("sec") or g("SEC") or None,
        "address":         g("budadd") or g("BUDADD") or None,
        "total_area_ping": _str_float(g("btotal") or g("BTOTAL")),
        "auction_date":    _roc_to_iso(sale_date_roc),
        "reserve_price":   _str_price(g("summinprc") or g("SUMMINPRC")),
        "hammer_price":    _str_price(g("sumfinprc") or g("SUMFINPRC")),
        "delivery_yn":     _yn(g("checkyn") or g("CHECKYN")),
        "vacant_yn":       _yn(g("emptyyn") or g("EMPTYYN")),
        "remote_bid_yn":   _yn(g("comm_yn") or g("COMM_YN")),
        "contamination":   g("newareano") or g("NEWAREANO") or None,
        "upload_date":     _roc_to_iso(upload_dt) if upload_dt else None,
        "upload_time":     upload_tm or None,
        "raw_json":        json.dumps(raw, ensure_ascii=False),
    }


_UPSERT_AUCTION = """
INSERT INTO auctions (
    court_code, court_name,
    case_year, case_type, case_no, case_division, auction_round,
    file_name, para, sale_type, prop_type,
    county_no, county_name, district, section,
    address, total_area_ping,
    auction_date, reserve_price, hammer_price,
    delivery_yn, vacant_yn, remote_bid_yn, contamination,
    upload_date, upload_time, raw_json
) VALUES (
    %(court_code)s, %(court_name)s,
    %(case_year)s, %(case_type)s, %(case_no)s, %(case_division)s, %(auction_round)s,
    %(file_name)s, %(para)s, %(sale_type)s, %(prop_type)s,
    %(county_no)s, %(county_name)s, %(district)s, %(section)s,
    %(address)s, %(total_area_ping)s,
    %(auction_date)s, %(reserve_price)s, %(hammer_price)s,
    %(delivery_yn)s, %(vacant_yn)s, %(remote_bid_yn)s, %(contamination)s,
    %(upload_date)s, %(upload_time)s, %(raw_json)s
)
ON DUPLICATE KEY UPDATE
    file_name       = VALUES(file_name),
    para            = VALUES(para),
    address         = VALUES(address),
    total_area_ping = VALUES(total_area_ping),
    auction_date    = VALUES(auction_date),
    reserve_price   = VALUES(reserve_price),
    hammer_price    = COALESCE(VALUES(hammer_price), hammer_price),
    delivery_yn     = VALUES(delivery_yn),
    vacant_yn       = VALUES(vacant_yn),
    remote_bid_yn   = VALUES(remote_bid_yn),
    contamination   = VALUES(contamination),
    upload_date     = VALUES(upload_date),
    upload_time     = VALUES(upload_time),
    raw_json        = VALUES(raw_json),
    updated_at      = CURRENT_TIMESTAMP
"""


def upsert_auction(row: Dict[str, Any]) -> int:
    """
    Upsert one auction row. Returns the auction.id (new or existing).
    """
    with get_cursor() as cur:
        cur.execute(_UPSERT_AUCTION, row)
        if cur.lastrowid:
            return cur.lastrowid
        # Row existed — fetch its id
        cur.execute(
            "SELECT id FROM auctions "
            "WHERE court_code=%s AND case_year=%s AND case_type=%s "
            "  AND case_no=%s AND auction_round=%s AND sale_type=%s",
            (row["court_code"], row["case_year"], row["case_type"],
             row["case_no"], row["auction_round"], row["sale_type"]),
        )
        return cur.fetchone()["id"]


_UPSERT_DETAIL = """
INSERT INTO auction_details (
    auction_id, pdf_url, pdf_local_path, pdf_text, pdf_json, detail_raw_json
) VALUES (
    %(auction_id)s, %(pdf_url)s, %(pdf_local_path)s,
    %(pdf_text)s, %(pdf_json)s, %(detail_raw_json)s
)
ON DUPLICATE KEY UPDATE
    pdf_url          = VALUES(pdf_url),
    pdf_local_path   = VALUES(pdf_local_path),
    pdf_text         = VALUES(pdf_text),
    pdf_json         = VALUES(pdf_json),
    detail_raw_json  = VALUES(detail_raw_json),
    fetched_at       = CURRENT_TIMESTAMP
"""


def upsert_detail(
    auction_id: int,
    pdf_url: Optional[str],
    pdf_local_path: Optional[str],
    pdf_text: str,
    pdf_structured: Optional[Dict],
    detail_raw: Optional[Dict],
) -> None:
    row = {
        "auction_id":      auction_id,
        "pdf_url":         pdf_url,
        "pdf_local_path":  pdf_local_path,
        "pdf_text":        pdf_text or None,
        "pdf_json":        json.dumps(pdf_structured, ensure_ascii=False)
                           if pdf_structured else None,
        "detail_raw_json": json.dumps(detail_raw, ensure_ascii=False)
                           if detail_raw else None,
    }
    with get_cursor() as cur:
        cur.execute(_UPSERT_DETAIL, row)


def log_run_start(run_type, court_code, sale_type, prop_type,
                  date_from, date_to) -> int:
    with get_cursor() as cur:
        cur.execute(
            """INSERT INTO crawler_runs
               (run_type, court_code, sale_type, prop_type,
                date_from, date_to, started_at, status)
               VALUES (%s, %s, %s, %s, %s, %s, NOW(), 'running')""",
            (run_type, court_code, sale_type, prop_type,
             date_from, date_to),
        )
        return cur.lastrowid


def log_run_finish(run_id: int, found: int, new: int, updated: int,
                   status: str = "success", error: str = None) -> None:
    with get_cursor() as cur:
        cur.execute(
            """UPDATE crawler_runs
               SET finished_at=NOW(), records_found=%s, records_new=%s,
                   records_updated=%s, status=%s, error_text=%s
               WHERE id=%s""",
            (found, new, updated, status, error, run_id),
        )
