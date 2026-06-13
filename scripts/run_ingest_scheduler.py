from __future__ import annotations

import argparse
import time
from datetime import datetime

from run_ingest_once import main as run_once


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run ingestion repeatedly without Airflow.")
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=1800,
        help="Seconds between ingestion runs. Default is 1800 seconds / 30 minutes.",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=0,
        help="Number of runs before exiting. Default 0 means run forever.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    completed = 0

    while True:
        print(f"[{datetime.now().isoformat(timespec='seconds')}] Scheduler tick")
        run_once()
        completed += 1

        if args.runs and completed >= args.runs:
            break

        time.sleep(args.interval_seconds)


if __name__ == "__main__":
    main()
