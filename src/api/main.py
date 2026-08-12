"""
Read-only API over the judicial_yuan MySQL data, plus the PWA static
frontend, served from one process on one port — so a phone on the same
Wi-Fi can reach both from a single URL with no CORS or separate host.

Run (from repo root):
  python scripts/run_api.py
or directly:
  uvicorn src.api.main:app --host 0.0.0.0 --port 8000

Then, from a phone on the same Wi-Fi as this machine, visit
http://<this-machine's-LAN-IP>:8000/ and "Add to Home Screen".
"""
from datetime import date
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import repository
from .schemas import AuctionDetail, AuctionListResponse, Court

app = FastAPI(title="Judicial Auction Valuator API", version="0.1.0")

# Permissive for local development on a LAN with no public exposure.
# Tighten this before deploying anywhere reachable off your own network.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/courts", response_model=List[Court])
def get_courts():
    return repository.list_courts()


@app.get("/api/auctions", response_model=AuctionListResponse)
def get_auctions(
    status: Optional[str] = None,
    court_code: Optional[str] = None,
    prop_type: Optional[str] = None,
    county_name: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    try:
        items, total = repository.list_auctions(
            status=status,
            court_code=court_code,
            prop_type=prop_type,
            county_name=county_name,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {"items": items, "total": total, "limit": limit, "offset": offset}


@app.get("/api/auctions/{auction_id}", response_model=AuctionDetail)
def get_auction(auction_id: int):
    auction = repository.get_auction(auction_id)
    if not auction:
        raise HTTPException(status_code=404, detail="Auction not found")
    return auction


# Mounted last: API routes above take precedence, this catches everything
# else (the PWA shell) so the whole app is reachable from one origin/port.
_STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="static")
