"""
Fetches the per-auction detail JSON (using `para` field) and derives the PDF URL.

Two data sources per auction:
  - filenm  → PDF path (e.g. /tpd/11503/xxx.pdf)  →  PDF_BASE_URL + filenm
  - para    → base64 key sent to DETAIL_URL as ?para=...
"""
import logging
from typing import Optional, Dict, Any

from .. import config
from .session import JudicialSession

logger = logging.getLogger(__name__)

# If the detail JSON also contains a PDF URL under one of these keys, prefer it.
# Otherwise we construct the URL from filenm directly.
_PDF_KEY_CANDIDATES = [
    "pdfUrl", "pdfurl", "PDF_URL", "fileUrl", "docUrl",
    "annUrl", "annurl", "htmUrl", "filenm", "FILENM",
]


def pdf_url_from_filenm(filenm: Optional[str]) -> Optional[str]:
    """Build the full PDF download URL from the filenm path returned by the search API.

    Flow: DO_VIEWPDF.htm?filenm=<path> → application/pdf bytes (streams directly).
    """
    if not filenm:
        return None
    path = filenm if filenm.startswith("/") else f"/{filenm}"
    return f"{config.PDF_DOWNLOAD_URL}?filenm={path}"


def _extract_pdf_url_from_detail(detail_data: Any) -> Optional[str]:
    """Walk known key paths in the detail JSON to find an explicit PDF URL."""
    if not isinstance(detail_data, dict):
        return None

    for container_key in (None, "data", "ht", "result"):
        obj = detail_data if container_key is None else detail_data.get(container_key)
        if isinstance(obj, list) and obj:
            obj = obj[0]
        if not isinstance(obj, dict):
            continue
        for key in _PDF_KEY_CANDIDATES:
            val = obj.get(key)
            if val and isinstance(val, str):
                if val.startswith("http"):
                    return val
                if val.startswith("/") and val.endswith(".pdf"):
                    return pdf_url_from_filenm(val)

    return None


def fetch_detail(
    session: JudicialSession,
    para: str,
    filenm: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Fetches detail JSON for one auction.

    Returns:
      raw_json  – full response dict from detail endpoint
      pdf_url   – resolved PDF URL (from detail JSON or constructed from filenm)
    """
    result: Dict[str, Any] = {"raw_json": None, "pdf_url": None}

    # Always try to build the PDF URL from filenm first (fast, no extra request)
    result["pdf_url"] = pdf_url_from_filenm(filenm)

    if not para:
        return result

    try:
        data = session.get_detail(para)
    except Exception as exc:
        # Detail endpoint returns HTML for some record types — not a fatal error;
        # the PDF URL is already resolved from filenm above.
        logger.debug("Detail fetch skipped para=%s: %s", para, exc)
        return result

    result["raw_json"] = data

    # If the detail JSON has a more specific PDF URL, prefer it
    detail_pdf = _extract_pdf_url_from_detail(data)
    if detail_pdf:
        result["pdf_url"] = detail_pdf

    return result
