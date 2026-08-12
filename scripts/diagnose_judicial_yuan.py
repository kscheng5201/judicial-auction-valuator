"""
Live diagnostic: tests every layer of the Judicial Yuan site against the
real site and prints raw responses. Useful when the source HTML/JSON
format changes and the parser starts failing silently.

Usage (from repo root):
  python scripts/diagnose_judicial_yuan.py
"""
import json
import sys
import time
from datetime import date, timedelta

import requests
from bs4 import BeautifulSoup

FORM_URL   = "https://aomp109.judicial.gov.tw/judbp/wkw/WHD1A02/V1.htm"
SEARCH_URL = "https://aomp109.judicial.gov.tw/judbp/wkw/WHD1A02/QUERY.htm"
DETAIL_URL = "https://kpic.judicial.gov.tw/judkp/wkw/WHD1A02_DETAIL/V1.htm"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    "Referer": FORM_URL,
}

def sep(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)

def dump(label, obj):
    print(f"\n--- {label} ---")
    if isinstance(obj, (dict, list)):
        print(json.dumps(obj, ensure_ascii=False, indent=2))
    else:
        print(obj)

def to_roc(d: date) -> str:
    return f"{d.year - 1911:03d}{d.month:02d}{d.day:02d}"


# ── STEP 1: fetch form page, extract CSRF ─────────────────────
sep("STEP 1 — GET form page, extract CSRF token")
session = requests.Session()
session.headers.update(HEADERS)

resp = session.get(FORM_URL, timeout=15)
print(f"Status: {resp.status_code}")
print(f"Cookies: {dict(session.cookies)}")

soup = BeautifulSoup(resp.text, "html.parser")
csrf_tag = soup.find("input", {"name": "_csrf"})
if not csrf_tag:
    print("ERROR: _csrf input not found in form page!")
    print("First 500 chars of response:")
    print(resp.text[:500])
    sys.exit(1)

csrf = csrf_tag["value"]
print(f"CSRF token: {csrf}")


# ── STEP 2: POST to QUERY.htm — one court, upcoming, 30 days ──
sep("STEP 2 — POST to QUERY.htm (court=TPD, saletype=1, proptype=C52)")
today     = date.today()
date_from = to_roc(today)
date_to   = to_roc(today + timedelta(days=30))
print(f"Date range (ROC): {date_from} → {date_to}  (Gregorian: {today} → {today+timedelta(days=30)})")

payload = {
    "court":         "TPD",
    "crtnm":         "臺灣臺北地方法院",
    "county":        "",
    "town":          "",
    "sec":           "",
    "proptype":      "C52",
    "saletype":      "1",
    "saledate1":     date_from,
    "saledate2":     date_to,
    "saleno":        "",
    "keyword":       "",
    "crmyy":         "",
    "crmid":         "",
    "crmno":         "",
    "dpt":           "",
    "minprice1":     "",
    "minprice2":     "",
    "area1":         "",
    "area2":         "",
    "debtor":        "",
    "ttitle":        "",
    "rrange":        "",
    "checkyn":       "",
    "emptyyn":       "",
    "comm_yn":       "",
    "stopitem":      "",
    "sorted_column": "A.SALEDATE,A.CRMYY,A.CRMID,A.CRMNO,A.SALENO,A.ROWID",
    "sorted_type":   "ASC",
    "pageNo":        "1",
    "pageSize":      "5",
    "_csrf":         csrf,
}

time.sleep(1)
resp2 = session.post(SEARCH_URL, data=payload, timeout=15)
print(f"Status: {resp2.status_code}")
print(f"Content-Type: {resp2.headers.get('Content-Type')}")

try:
    data = resp2.json()
except Exception as e:
    print(f"ERROR parsing JSON: {e}")
    print("Raw response (first 1000 chars):")
    print(resp2.text[:1000])
    sys.exit(1)

dump("Top-level keys", list(data.keys()))
dump("status / messageText", {
    "status": data.get("status"),
    "messageText": data.get("messageText"),
})
dump("pageInfo", data.get("pageInfo"))

records = data.get("data") or []
print(f"\nRecords returned: {len(records)}")

if records:
    dump("First record — ALL field names + values", records[0])
    if len(records) > 1:
        print(f"\nSecond record keys: {list(records[1].keys())}")
else:
    print("No records found for this query.")
    print("Trying wider date range (today → +90 days) ...")

    payload["saledate2"] = to_roc(today + timedelta(days=90))
    payload["pageSize"]  = "3"
    time.sleep(1)
    resp3 = session.post(SEARCH_URL, data=payload, timeout=15)
    try:
        data3 = resp3.json()
        records3 = data3.get("data") or []
        print(f"Records with 90-day window: {len(records3)}")
        if records3:
            dump("First record (90-day window)", records3[0])
        else:
            dump("Full response", data3)
    except Exception as e:
        print(f"ERROR: {e}")
        print(resp3.text[:500])


# ── STEP 3: historical 拍定價格 (saletype=5) ──────────────────
sep("STEP 3 — POST to QUERY.htm (saletype=5, last 30 days)")
hist_from = to_roc(today - timedelta(days=30))
hist_to   = to_roc(today)
print(f"Date range (ROC): {hist_from} → {hist_to}")

payload2 = dict(payload)
payload2.update({
    "saletype":  "5",
    "saledate1": hist_from,
    "saledate2": hist_to,
    "pageSize":  "3",
})
time.sleep(1)
resp4 = session.post(SEARCH_URL, data=payload2, timeout=15)
try:
    data4 = resp4.json()
    records4 = data4.get("data") or []
    print(f"Status: {data4.get('status')}  Records: {len(records4)}")
    if records4:
        dump("First 拍定 record", records4[0])
    else:
        dump("Full response", data4)
except Exception as e:
    print(f"ERROR: {e}\n{resp4.text[:500]}")


# ── STEP 4: detail endpoint ───────────────────────────────────
filenm = None
for r in (records or []):
    filenm = r.get("filenm") or r.get("FILENM")
    if filenm:
        break

sep(f"STEP 4 — GET detail endpoint (filenm={filenm!r})")
if filenm:
    time.sleep(1)
    resp5 = session.get(DETAIL_URL, params={"para": filenm}, timeout=15)
    print(f"Status: {resp5.status_code}")
    try:
        detail = resp5.json()
        dump("Top-level keys", list(detail.keys()))
        dump("status / messageText", {
            "status": detail.get("status"),
            "messageText": detail.get("messageText"),
        })
        inner = detail.get("data") or detail.get("ht") or detail.get("result")
        if isinstance(inner, list) and inner:
            dump("detail.data[0] — ALL fields", inner[0])
        elif isinstance(inner, dict):
            dump("detail.data — ALL fields", inner)
        else:
            dump("Full detail response", detail)
    except Exception as e:
        print(f"ERROR parsing detail JSON: {e}")
        print(resp5.text[:1000])
else:
    print("No filenm found in step 2 results — skipping detail test.")

print("\n\nDiagnosis complete.")
