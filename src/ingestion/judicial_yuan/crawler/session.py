"""
Manages an HTTP session against the judicial auction site.

The site requires three things for every QUERY.htm POST to succeed:
  1. Session cookies  — obtained by loading the outermost frameset page
  2. _csrf token      — hidden field in V1.htm (search form)
  3. token            — hidden field in V2.htm (results frame)
  4. X-Requested-With: XMLHttpRequest  — jQuery AJAX header the server validates
  5. Referer: V2.htm  — POST must appear to originate from the results frame
"""
import time
import requests
from bs4 import BeautifulSoup

from .. import config
from ..retry import with_retry

# Headers that mimic jQuery $.ajax() exactly
_AJAX_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    "X-Requested-With": "XMLHttpRequest",
}


def _tag_val(soup: BeautifulSoup, name: str) -> str:
    tag = soup.find("input", {"name": name})
    return tag.get("value", "") if tag else ""


class JudicialSession:
    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update(_AJAX_HEADERS)
        self._csrf  = None
        self._token = None

    def refresh_csrf(self):
        """
        Load frameset → V1 → V2 in order to establish session cookies,
        then extract the _csrf and token fields the server embeds in V2.htm.
        """
        # 1. Frameset — sets the initial session cookies
        with_retry(self._session.get, config.FRAMESET_URL, timeout=config.REQUEST_TIMEOUT)
        time.sleep(0.3)

        # 2. V1 (search form) — CSRF token
        r1 = with_retry(self._session.get, config.FORM_URL, timeout=config.REQUEST_TIMEOUT)
        r1.raise_for_status()

        # 3. V2 (results frame) — token + refreshed CSRF
        r2 = with_retry(self._session.get, config.RESULTS_URL, timeout=config.REQUEST_TIMEOUT)
        r2.raise_for_status()
        soup2 = BeautifulSoup(r2.text, "html.parser")

        self._csrf  = _tag_val(soup2, "_csrf")
        self._token = _tag_val(soup2, "token")

        if not self._csrf:
            raise RuntimeError("Could not find _csrf in V2.htm")
        if not self._token:
            raise RuntimeError("Could not find token in V2.htm")

    def post_query(self, payload: dict) -> dict:
        """
        POST to QUERY.htm. Refreshes tokens if not yet obtained.
        Returns parsed JSON response dict.
        """
        if self._csrf is None:
            self.refresh_csrf()

        payload["_csrf"]  = self._csrf
        payload["token"]  = self._token
        time.sleep(config.REQUEST_DELAY)

        resp = with_retry(
            self._session.post,
            config.SEARCH_URL,
            data=payload,
            headers={"Referer": config.RESULTS_URL},
            timeout=config.REQUEST_TIMEOUT,
        )
        resp.raise_for_status()

        try:
            data = resp.json()
        except ValueError:
            raise RuntimeError(f"Non-JSON response from QUERY.htm: {resp.text[:300]}")

        return data

    def get_detail(self, para: str) -> dict:
        """Fetch per-auction detail JSON using the `para` field from the search result."""
        time.sleep(config.REQUEST_DELAY)
        resp = with_retry(
            self._session.get,
            config.DETAIL_URL,
            params={"para": para},
            headers={"Referer": config.RESULTS_URL},
            timeout=config.REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        try:
            return resp.json()
        except ValueError:
            raise RuntimeError(
                f"Non-JSON from detail endpoint (para={para})"
            )

    def download_pdf(self, url: str) -> bytes:
        """Download a PDF and return raw bytes."""
        time.sleep(config.REQUEST_DELAY)
        resp = with_retry(self._session.get, url, timeout=config.REQUEST_TIMEOUT * 2)
        resp.raise_for_status()
        return resp.content
