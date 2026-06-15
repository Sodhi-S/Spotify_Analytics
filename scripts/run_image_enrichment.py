from __future__ import annotations

import argparse

from app.core.config import get_settings
from app.pipeline.image_enrichment import (
    rebuild_image_models,
    run_all_image_enrichment,
    run_image_enrichment,
)


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Backfill album covers and artist images.")
    parser.add_argument("--track-limit", type=int, default=settings.image_enrichment_track_limit)
    parser.add_argument("--artist-limit", type=int, default=settings.image_enrichment_artist_limit)
    parser.add_argument("--all", action="store_true", help="Process every unattempted image target.")
    parser.add_argument("--batch-size", type=int, default=settings.image_enrichment_track_limit)
    parser.add_argument(
        "--max-batches",
        type=int,
        default=0,
        help="Maximum batches for --all. Default 0 means no cap.",
    )
    parser.add_argument(
        "--retry-unresolved",
        action="store_true",
        help="Retry targets that were previously attempted but unresolved.",
    )
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument(
        "--no-artist-album-fallback",
        action="store_true",
        help="Do not use representative album artwork when no artist photo is available.",
    )
    parser.add_argument("--skip-dbt", action="store_true")
    args = parser.parse_args()

    print("Running image enrichment...")
    if args.all:
        print(
            run_all_image_enrichment(
                batch_size=args.batch_size,
                refresh=args.refresh,
                retry_unresolved=args.retry_unresolved,
                use_album_fallback=not args.no_artist_album_fallback,
                max_batches=args.max_batches,
            )
        )
    else:
        print(
            run_image_enrichment(
                track_limit=args.track_limit,
                artist_limit=args.artist_limit,
                refresh=args.refresh,
                retry_unresolved=args.retry_unresolved,
                use_album_fallback=not args.no_artist_album_fallback,
            )
        )

    if not args.skip_dbt:
        print("Rebuilding image-enabled dbt models...")
        print(rebuild_image_models())


if __name__ == "__main__":
    main()
