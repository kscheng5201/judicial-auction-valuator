"""
Entry point for the Judicial Yuan auction crawler.

Usage (from repo root):
  python scripts/run_judicial_yuan_crawler.py upcoming      # run the upcoming auction crawl once now
  python scripts/run_judicial_yuan_crawler.py historical    # run the historical 拍定價格 crawl once now
  python scripts/run_judicial_yuan_crawler.py all           # run both pipelines once now
"""
import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("run_judicial_yuan_crawler")


def main():
    parser = argparse.ArgumentParser(description="Judicial Yuan auction crawler")
    parser.add_argument(
        "command",
        choices=["upcoming", "historical", "all"],
        help="Which pipeline to run",
    )
    args = parser.parse_args()

    if args.command in ("upcoming", "all"):
        from src.ingestion.judicial_yuan.pipeline.upcoming import run_upcoming
        run_upcoming()

    if args.command in ("historical", "all"):
        from src.ingestion.judicial_yuan.pipeline.historical import run_historical
        run_historical()


if __name__ == "__main__":
    main()
