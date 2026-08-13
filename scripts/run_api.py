"""
Runs the auction API + PWA frontend (single process, single port).

Usage (from repo root):
  python scripts/run_api.py

Then, from a phone on the same Wi-Fi as this machine, visit:
  http://<this-machine's-LAN-IP>:<port>/
and use the browser's "Add to Home Screen" to install it as an app icon.

Find this machine's LAN IP with, e.g.:
  macOS:   ipconfig getifaddr en0
  Linux:   hostname -I
  Windows: ipconfig
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import uvicorn

from src.api.config import API_HOST, API_PORT

if __name__ == "__main__":
    uvicorn.run("src.api.main:app", host=API_HOST, port=API_PORT, reload=False)
