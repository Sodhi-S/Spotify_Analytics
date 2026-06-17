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
    fallback_group = parser.add_mutually_exclusive_group()
    fallback_group.add_argument(
        "--artist-album-fallback",
        action="store_true",
        default=settings.image_enrichment_artist_album_fallback,
        help="Use representative album artwork when no artist photo is available.",
    )
    fallback_group.add_argument(
        "--no-artist-album-fallback",
        action="store_true",
        help="Do not use representative album artwork when no artist photo is available.",
    )
    parser.add_argument(
        "--tracks-only",
        action="store_true",
        help="Only enrich track album artwork. Skips artist image lookups.",
    )
    parser.add_argument(
        "--artists-only",
        action="store_true",
        help="Only enrich artist images. Skips track album artwork.",
    )
    parser.add_argument("--skip-dbt", action="store_true")
    args = parser.parse_args()
    if args.tracks_only and args.artists_only:
        parser.error("--tracks-only and --artists-only cannot be used together.")
    use_album_fallback = args.artist_album_fallback and not args.no_artist_album_fallback

    print("Running image enrichment...")
    if args.all:
        print(
            run_all_image_enrichment(
                batch_size=args.batch_size,
                refresh=args.refresh,
                retry_unresolved=args.retry_unresolved,
                use_album_fallback=use_album_fallback,
                max_batches=args.max_batches,
                include_tracks=not args.artists_only,
                include_artists=not args.tracks_only,
            )
        )
    else:
        print(
            run_image_enrichment(
                track_limit=0 if args.artists_only else args.track_limit,
                artist_limit=0 if args.tracks_only else args.artist_limit,
                refresh=args.refresh,
                retry_unresolved=args.retry_unresolved,
                use_album_fallback=use_album_fallback,
            )
        )

    if not args.skip_dbt:
        print("Rebuilding image-enabled dbt models...")
        print(rebuild_image_models())


if __name__ == "__main__":
    main()
