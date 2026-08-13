"""
Read-only queries against the judicial_yuan MySQL schema for the API layer.

Reuses src/ingestion/judicial_yuan/db/connection.py directly rather than
introducing a separate shared db module — there's only one data source
today. Worth hoisting to a shared src/db/ once enrichment/valuation need
direct DB access too, per the note in that module.
"""
import json
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from src.ingestion.judicial_yuan.db.connection import get_cursor

_STATUS_SALE_TYPES = {
    "upcoming": (1, 4),
    "historical": (5,),
}

_LIST_COLUMNS = """
    id, court_code, court_name, case_year, case_type, case_no,
    auction_round, sale_type, prop_type, county_name, district,
    address, total_area_ping, auction_date, reserve_price,
    hammer_price, delivery_yn, vacant_yn
"""


def _parse_json_field(value: Any) -> Any:
    """PyMySQL returns JSON columns as raw text, not parsed objects."""
    if value is None or isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return None


def list_auctions(
    status: Optional[str] = None,
    court_code: Optional[str] = None,
    prop_type: Optional[str] = None,
    county_name: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    limit: int = 20,
    offset: int = 0,
) -> Tuple[List[Dict[str, Any]], int]:
    where: List[str] = []
    params: List[Any] = []

    if status:
        sale_types = _STATUS_SALE_TYPES.get(status)
        if not sale_types:
            raise ValueError(f"Unknown status: {status!r} (expected 'upcoming' or 'historical')")
        where.append(f"sale_type IN ({','.join(['%s'] * len(sale_types))})")
        params.extend(sale_types)
    if court_code:
        where.append("court_code = %s")
        params.append(court_code)
    if prop_type:
        where.append("prop_type = %s")
        params.append(prop_type)
    if county_name:
        where.append("county_name = %s")
        params.append(county_name)
    if date_from:
        where.append("auction_date >= %s")
        params.append(date_from)
    if date_to:
        where.append("auction_date <= %s")
        params.append(date_to)

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    with get_cursor() as cur:
        cur.execute(f"SELECT COUNT(*) AS total FROM auctions {where_sql}", params)
        total = cur.fetchone()["total"]

        cur.execute(
            f"""SELECT {_LIST_COLUMNS} FROM auctions {where_sql}
                ORDER BY auction_date DESC, id DESC
                LIMIT %s OFFSET %s""",
            params + [limit, offset],
        )
        rows = cur.fetchall()

    return rows, total


def get_auction(auction_id: int) -> Optional[Dict[str, Any]]:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM auctions WHERE id = %s", (auction_id,))
        auction = cur.fetchone()
        if not auction:
            return None
        auction["raw_json"] = _parse_json_field(auction.get("raw_json"))

        cur.execute(
            "SELECT pdf_url, pdf_local_path, pdf_text, pdf_json, detail_raw_json, fetched_at "
            "FROM auction_details WHERE auction_id = %s",
            (auction_id,),
        )
        detail = cur.fetchone()
        if detail:
            detail["pdf_json"] = _parse_json_field(detail.get("pdf_json"))
            detail["detail_raw_json"] = _parse_json_field(detail.get("detail_raw_json"))
        auction["detail"] = detail

    return auction


def list_courts() -> List[Dict[str, Any]]:
    with get_cursor() as cur:
        cur.execute("SELECT code, name FROM courts ORDER BY code")
        return cur.fetchall()
