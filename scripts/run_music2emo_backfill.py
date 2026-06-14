from __future__ import annotations

import argparse

from app.pipeline.music2emo_jobs import (
    fetch_music2emo_previews,
    find_unscored_music2emo_tracks,
    rebuild_music2emo_models,
    run_music2emo_inference,
    run_music2emo_pipeline,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill Music2Emo track emotion features.")
    parser.add_argument("--preview-limit", type=int, default=100)
    parser.add_argument("--inference-limit", type=int, default=25)
    parser.add_argument("--skip-preview", action="store_true")
    parser.add_argument("--skip-inference", action="store_true")
    parser.add_argument("--skip-dbt", action="store_true")
    parser.add_argument("--all", action="store_true", help="Keep running batches until no tracks remain.")
    parser.add_argument("--max-batches", type=int, default=0, help="Safety cap for --all. Default 0 means no cap.")
    args = parser.parse_args()

    print("Pending before:")
    print(find_unscored_music2emo_tracks())

    if args.all:
        batch = 0
        while True:
            pending = find_unscored_music2emo_tracks(
                limit=max(args.preview_limit, args.inference_limit)
            )
            if not pending["pending_preview_lookup"] and not pending["pending_inference"]:
                break
            if args.max_batches and batch >= args.max_batches:
                break

            batch += 1
            print(f"Running Music2Emo batch {batch}...")
            result = run_music2emo_pipeline(
                preview_limit=args.preview_limit,
                inference_limit=args.inference_limit,
                rebuild_models=not args.skip_dbt,
            )
            print(result)

        print("Pending after:")
        print(find_unscored_music2emo_tracks())
        return

    if not args.skip_preview and not args.skip_inference:
        result = run_music2emo_pipeline(
            preview_limit=args.preview_limit,
            inference_limit=args.inference_limit,
            rebuild_models=not args.skip_dbt,
        )
        if "dbt_before" in result:
            print("Refreshing dbt track models before preview lookup...")
            print(result["dbt_before"])
        print("Fetching iTunes previews...")
        print(result["preview_lookup"])
        print("Running Music2Emo inference...")
        print(result["inference"])
        if not args.skip_dbt:
            print("Rebuilding dbt mood models...")
            print(result["dbt_after"])
        print("Pending after:")
        print(result["pending_after"])
        return

    if not args.skip_preview:
        print("Fetching iTunes previews...")
        print(fetch_music2emo_previews(limit=args.preview_limit))

    if not args.skip_inference:
        print("Running Music2Emo inference...")
        print(run_music2emo_inference(limit=args.inference_limit))

    if not args.skip_dbt:
        print("Rebuilding dbt mood models...")
        print(rebuild_music2emo_models())

    print("Pending after:")
    print(find_unscored_music2emo_tracks())


if __name__ == "__main__":
    main()
