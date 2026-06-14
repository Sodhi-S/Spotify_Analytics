from __future__ import annotations

import argparse
from pathlib import Path

from app.pipeline.itunes_audit import export_no_itunes_preview_tracks


def main() -> None:
    parser = argparse.ArgumentParser(description="Export tracks still missing iTunes previews.")
    parser.add_argument("--path", type=Path, default=None)
    args = parser.parse_args()

    print(export_no_itunes_preview_tracks(args.path) if args.path else export_no_itunes_preview_tracks())


if __name__ == "__main__":
    main()
