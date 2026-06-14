# Music2Emo Backfill Runbook

Music2Emo scores tracks from audio previews and writes normalized valence/energy into Postgres.

## 1. Create A Separate Worker Env

Use Python 3.10 for this worker.

```bash
conda create -n music2emo python=3.10
conda activate music2emo
conda install ffmpeg -c conda-forge
pip install -r requirements-music2emo.txt
```

`requirements-music2emo.txt` pins `torch==2.2.2` and `torchaudio==2.2.2` because some macOS/Python environments do not expose newer Torch wheels through `pip`. If Torch still fails through `pip`, install Torch with Conda first:

```bash
conda install pytorch==2.2.2 torchaudio==2.2.2 -c pytorch
pip install -r requirements-music2emo.txt --no-deps
```

The worker requirements intentionally do not include `backend/requirements.txt`. The backend currently allows newer analytics dependencies, while Music2Emo/audio packages are more reliable with NumPy 1.x, `numba==0.59.1`, and `llvmlite==0.42.0` on macOS.

`ffmpeg` is required because iTunes returns AAC/M4A previews, while the model stack is much more reliable when the job converts those previews to WAV first.

Install the Music2Emo package from the upstream project. The Hugging Face model card points to the GitHub repo:

```bash
git clone https://github.com/AMAAI-Lab/Music2Emotion /tmp/Music2Emotion
```

Do not run `/tmp/Music2Emotion/requirements.txt` on this machine unless you edit its Torch pins first. The upstream file asks for `torch==2.3.1`, but this macOS/Python setup only exposes Torch wheels up to `2.2.2`.

The upstream repo is not an installable Python package, so do not run `pip install -e /tmp/Music2Emotion`. Point this app at the cloned source repo instead:

```bash
export MUSIC2EMO_REPO_PATH=/tmp/Music2Emotion
```

You can also put this in the project `.env`:

```bash
MUSIC2EMO_REPO_PATH=/tmp/Music2Emotion
MUSIC2EMO_MODEL_WEIGHTS=/tmp/Music2Emotion/saved_models/J_all.ckpt
```

If `MUSIC2EMO_MODEL_WEIGHTS` is omitted, the app defaults to `saved_models/J_all.ckpt` inside `MUSIC2EMO_REPO_PATH`.

## 2. Initialize The Emotion Table

From the project root:

```bash
./scripts/db_init.sh
```

That applies `backend/sql/004_track_emotion_features.sql`.

## 3. Run A Small Test Batch

```bash
PYTHONPATH=backend python scripts/run_music2emo_backfill.py \
  --preview-limit 10 \
  --inference-limit 3
```

The script:

1. Finds tracks without emotion features.
2. Looks up iTunes preview URLs.
3. Downloads each preview to a temp file.
4. Runs Music2Emo.
5. Stores raw 1-9 valence/arousal and normalized 0-1 valence/energy.
6. Rebuilds `dim_tracks` and `mart_listening_summary`.

## 4. Run Larger Batches

```bash
PYTHONPATH=backend python scripts/run_music2emo_backfill.py \
  --preview-limit 100 \
  --inference-limit 25
```

Keep the inference limit modest at first. This is a model job, not a web request path.

To process everything currently reachable in the database, run:

```bash
PYTHONPATH=backend python scripts/run_music2emo_backfill.py \
  --preview-limit 100 \
  --inference-limit 25 \
  --all
```

Use `--max-batches 3` if you want a safety cap while testing. Tracks without an iTunes preview are marked in `raw.track_emotion_features` with an error message so the full backfill does not retry the same impossible matches forever.

## 5. Run Automatically After Last.fm Ingestion

The local ingestion command now runs Music2Emo after Last.fm ingestion when this setting is enabled:

```bash
MUSIC2EMO_RUN_AFTER_INGEST=true
MUSIC2EMO_PREVIEW_LIMIT=100
MUSIC2EMO_INFERENCE_LIMIT=25
```

Run one full local pipeline tick:

```bash
PYTHONPATH=backend python scripts/run_ingest_once.py
```

Run it repeatedly like cron:

```bash
PYTHONPATH=backend:scripts python scripts/run_ingest_scheduler.py --interval-seconds 1800
```

Each tick:

1. Ingests Last.fm data into raw tables.
2. Rebuilds dbt track models so new raw tracks enter `dim_tracks`.
3. Finds iTunes previews for unscored tracks.
4. Converts previews to WAV.
5. Runs Music2Emo for up to `MUSIC2EMO_INFERENCE_LIMIT` tracks.
6. Stores results in `raw.track_emotion_features`.
7. Rebuilds dbt track/summary models so the app sees the new mood values.
8. Exports tracks still missing iTunes previews to `exports/no_itunes_preview_tracks.csv`.

Refresh only the missing-preview export:

```bash
PYTHONPATH=backend python scripts/export_no_itunes_preview_tracks.py
```

## 6. Production Shape

Do not run Music2Emo inside FastAPI request handlers.

Use:

- FastAPI for reads/writes
- Postgres for storage
- a worker or scheduled job for Music2Emo
- dbt after inference batches

Audio preview files are temporary and deleted after inference.

## iTunes Preview API

The app uses Apple's public iTunes Search API to find preview URLs. No API key is required.

Code locations:

- `backend/app/ingestion/itunes.py` defines the client.
- `backend/app/pipeline/music2emo_jobs.py` calls the client before inference.

Not every track has a usable iTunes preview, so some rows can remain unscored until a better audio source is added.

## Manual Apple Music Overrides

For tracks that exist in Apple Music but are not returned by the public iTunes Search API, add manual overrides.

Create a local file:

```bash
data/manual_itunes_overrides.csv
```

Use this shape:

```csv
track_id,artist_name,track_name,apple_music_url,preview_url
da952f8252d1a2fc7caeca310b155dde,plaqueboymax,wyd (feat. Bryson Tiller),https://music.apple.com/us/song/wyd/1869168174,
```

`track_id` is preferred because it avoids artist/title ambiguity. `apple_music_url` can be a normal Apple Music song link; the script extracts the numeric ID and calls the iTunes Lookup API to get the direct `previewUrl`. If you already have the direct audio preview URL, put it in `preview_url`.

Apply overrides and run Music2Emo only for those fixed tracks:

```bash
PYTHONPATH=backend python scripts/apply_itunes_overrides.py
```

After overrides run, the missing-preview export is refreshed automatically.

Debug without inference:

```bash
PYTHONPATH=backend python scripts/apply_itunes_overrides.py --skip-inference --skip-dbt
```
