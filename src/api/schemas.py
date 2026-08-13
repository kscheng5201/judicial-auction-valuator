from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class Court(BaseModel):
    code: str
    name: str


class AuctionSummary(BaseModel):
    id: int
    court_code: str
    court_name: str
    case_year: int
    case_type: str
    case_no: str
    auction_round: int
    sale_type: int
    prop_type: str
    county_name: Optional[str] = None
    district: Optional[str] = None
    address: Optional[str] = None
    total_area_ping: Optional[Decimal] = None
    auction_date: Optional[date] = None
    reserve_price: Optional[int] = None
    hammer_price: Optional[int] = None
    delivery_yn: Optional[str] = None
    vacant_yn: Optional[str] = None


class AuctionListResponse(BaseModel):
    items: List[AuctionSummary]
    total: int
    limit: int
    offset: int


class AuctionDetailInfo(BaseModel):
    pdf_url: Optional[str] = None
    pdf_local_path: Optional[str] = None
    pdf_text: Optional[str] = None
    pdf_json: Optional[Dict[str, Any]] = None
    detail_raw_json: Optional[Dict[str, Any]] = None
    fetched_at: Optional[datetime] = None


class AuctionDetail(AuctionSummary):
    case_division: str
    file_name: Optional[str] = None
    county_no: Optional[str] = None
    section: Optional[str] = None
    remote_bid_yn: Optional[str] = None
    contamination: Optional[str] = None
    upload_date: Optional[date] = None
    upload_time: Optional[str] = None
    raw_json: Optional[Dict[str, Any]] = None
    first_seen_at: datetime
    updated_at: datetime
    detail: Optional[AuctionDetailInfo] = None
