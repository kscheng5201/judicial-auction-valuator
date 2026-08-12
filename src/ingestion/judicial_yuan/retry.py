"""
Retry-with-backoff for the transient network failures this crawler
actually sees in practice — most commonly, the desktop it runs on not
being connected to the internet yet when the scheduled job fires.

Deliberately narrow: only retries requests.exceptions.RequestException
(connection errors, timeouts, etc). A non-2xx response that raises via
raise_for_status() is also a RequestException, so a dead endpoint or a
server error gets retried too — that's fine, it just exhausts attempts
and re-raises like any other exhausted retry.
"""
import logging
import time

import requests

from . import config

logger = logging.getLogger(__name__)


def with_retry(func, *args, **kwargs):
    """Call func(*args, **kwargs), retrying on RequestException with backoff."""
    last_exc = None
    for attempt in range(1, config.RETRY_MAX_ATTEMPTS + 1):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.RequestException as exc:
            last_exc = exc
            if attempt == config.RETRY_MAX_ATTEMPTS:
                break
            delay = config.RETRY_BASE_DELAY * (2 ** (attempt - 1))
            logger.warning(
                "Network call failed (attempt %d/%d): %s — retrying in %.0fs",
                attempt, config.RETRY_MAX_ATTEMPTS, exc, delay,
            )
            time.sleep(delay)
    raise last_exc
