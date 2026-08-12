"""
Best-effort alerting for pipeline failures.

Two independent, optional channels:
  - macOS desktop notification via `osascript` — the crawler currently
    runs as a background process on the same desktop a person is
    using, so a visible notification is the fastest way to surface a
    failure that would otherwise only exist as a log line.
  - Generic webhook POST (JUDICIAL_YUAN_ALERT_WEBHOOK_URL), e.g. a
    Slack incoming webhook, for visibility when nobody is at that
    desktop.

Alerting must never crash the pipeline it's reporting on — every
failure to send is caught and logged, not raised.
"""
import json
import logging
import platform
import subprocess

import requests

from . import config

logger = logging.getLogger(__name__)


def send_alert(subject: str, message: str) -> None:
    logger.error("%s: %s", subject, message)
    _notify_desktop(subject, message)
    _notify_webhook(subject, message)


def _notify_desktop(subject: str, message: str) -> None:
    if platform.system() != "Darwin":
        return
    # json.dumps quotes with " and escapes \ and " the same way AppleScript
    # string literals expect — good enough for one-line alert text.
    script = (
        f"display notification {json.dumps(message)} "
        f"with title {json.dumps(subject)}"
    )
    try:
        subprocess.run(["osascript", "-e", script], timeout=5, check=False)
    except Exception as exc:
        logger.debug("Desktop notification failed: %s", exc)


def _notify_webhook(subject: str, message: str) -> None:
    if not config.ALERT_WEBHOOK_URL:
        return
    try:
        requests.post(
            config.ALERT_WEBHOOK_URL,
            json={"text": f"{subject}\n{message}"},
            timeout=10,
        )
    except Exception as exc:
        logger.debug("Webhook alert failed: %s", exc)
