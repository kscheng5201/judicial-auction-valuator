"""
Downloads a PDF, saves it to disk, extracts text and structured fields.
"""
import io
import logging
import re
from pathlib import Path
from typing import Dict, Any

import pdfplumber

from .. import config
from .session import JudicialSession

logger = logging.getLogger(__name__)


def _local_path(court_code: str, file_name: str) -> Path:
    safe_name = re.sub(r"[^\w\-.]", "_", file_name)
    if not safe_name.endswith(".pdf"):
        safe_name += ".pdf"
    dest = Path(config.PDF_DIR) / court_code / safe_name
    dest.parent.mkdir(parents=True, exist_ok=True)
    return dest


def _extract_text(pdf_bytes: bytes) -> str:
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
        return "\n\n".join(pages).strip()
    except Exception as exc:
        logger.warning("pdfplumber extraction failed: %s", exc)
        return ""


def _parse_structured(text: str) -> Dict[str, Any]:
    """
    Best-effort extraction of key-value pairs from the auction notice text.
    Returns a JSON-serialisable dict.
    """
    fields: Dict[str, Any] = {}

    # Lines are prefixed with line numbers (e.g. "05 ") — strip them before matching.
    clean = re.sub(r"(?m)^\d{2,3}\s+", "", text)

    patterns = {
        "case_number":    r"案\s*號[：:]\s*(.+)",
        "debtor":         r"債\s*務\s*人[：:]\s*(.+)",
        "creditor":       r"債\s*權\s*人[：:]\s*(.+)",
        "auction_date":   r"拍賣日期[：:]\s*(.+)",
        "location":       r"坐\s*落[：:]\s*(.+)",
        "area":           r"面\s*積[：:]\s*(.+)",
        "reserve_price":  r"底\s*[价價][：:]\s*(.+)",
        "appraisal":      r"鑑\s*定\s*[价價][：:]\s*(.+)",
        "rights":         r"權\s*利\s*範\s*圍[：:]\s*(.+)",
        "viewing_date":   r"看\s*屋\s*日期[：:]\s*(.+)",
        "bidding_method": r"投\s*標\s*方\s*式[：:]\s*(.+)",
        "publish_date":   r"發文日期[：:]\s*(.+)",
        "case_id":        r"發文字號[：:]\s*(.+)",
    }

    for field, pattern in patterns.items():
        match = re.search(pattern, clean)
        if match:
            fields[field] = match.group(1).strip()

    return fields


def fetch_and_store_pdf(
    session: JudicialSession,
    pdf_url: str,
    court_code: str,
    file_name: str,
) -> Dict[str, Any]:
    """
    Downloads PDF, saves to disk, extracts text + structured fields.
    Returns dict with keys: local_path, text, structured_json.
    """
    result = {"local_path": None, "text": "", "structured_json": None}

    local_path = _local_path(court_code, file_name)

    # Use cached file if already downloaded
    if local_path.exists():
        logger.debug("PDF already on disk: %s", local_path)
        pdf_bytes = local_path.read_bytes()
    else:
        try:
            pdf_bytes = session.download_pdf(pdf_url)
        except Exception as exc:
            logger.warning("PDF download failed url=%s: %s", pdf_url, exc)
            return result

        local_path.write_bytes(pdf_bytes)
        logger.info("PDF saved: %s (%d bytes)", local_path, len(pdf_bytes))

    text = _extract_text(pdf_bytes)
    structured = _parse_structured(text) if text else {}

    result["local_path"] = str(local_path.relative_to(Path(config.PDF_DIR).parent))
    result["text"] = text
    result["structured_json"] = structured
    return result
