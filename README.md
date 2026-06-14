# Music Listening Intelligence Platform

Local data engineering project for Last.fm scrobbles, iTunes preview-based Music2Emo mood scoring, dbt marts, quality gates, Airflow orchestration, and a FastAPI + React analytics dashboard.

## What Is Implemented

- Last.fm ingestion jobs for recent tracks, track tags, artist info, artist tags, and user chart snapshots.
- Open-Meteo daily weather ingestion.
- iTunes preview lookup plus Music2Emo inference for track-level valence, energy, and mood labels.
- Raw PostgreSQL schema with incremental metadata, dedupe keys, and `raw.raw_failed`.
- `raw.track_emotion_features` storage for Music2Emo model outputs and inference failures.
- dbt staging, intermediate, mart, and SCD Type 2 artist snapshot models.
- Executable SQL quality gate plus Great Expectations suite definitions.
- Airflow DAGs for Last.fm, weather, mood classification, data quality, and dbt transforms.
- `GET /api/stats/overview` FastAPI endpoint.
- React/TypeScript overview, top tracks, moods, weather, and settings views.
- Optional frontend privacy mode that hides exact listening counts in screenshots/demos.

## Setup

1. Create a virtual environment and install backend/dev dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

2. Create `.env` from `.env.example` and fill in `LASTFM_API_KEY`, `LASTFM_USERNAME`, `DB_CONNECTION_STRING`, and `OPENMETEO_CITY`.

3. Initialize the raw PostgreSQL schema:

```bash
psql postgresql://postgres:postgres@localhost:5432/music_intelligence -f backend/sql/001_raw_schema.sql
```

4. Set up Music2Emo if you want AI mood/energy/valence population:

```bash
conda create -n music2emo python=3.10
conda activate music2emo
conda install ffmpeg -c conda-forge
pip install -r requirements-music2emo.txt
git clone https://github.com/AMAAI-Lab/Music2Emotion /tmp/Music2Emotion
```

Then set these in `.env`:

```bash
MUSIC2EMO_REPO_PATH=/tmp/Music2Emotion
MUSIC2EMO_MODEL_WEIGHTS=/tmp/Music2Emotion/saved_models/J_all.ckpt
MUSIC2EMO_RUN_AFTER_INGEST=true
MUSIC2EMO_PREVIEW_LIMIT=100
MUSIC2EMO_INFERENCE_LIMIT=25
```

5. Run the local ingestion path:

```bash
PYTHONPATH=backend python scripts/run_ingest_once.py
```

That one command:

1. Ingests Last.fm data into raw tables.
2. Rebuilds dbt track models so new tracks enter `dim_tracks`.
3. Looks up iTunes preview URLs.
4. Converts previews to WAV.
5. Runs Music2Emo inference.
6. Writes AI outputs into `raw.track_emotion_features`.
7. Rebuilds dbt mood/listening models.
8. Ingests current and historical weather data.

To run it repeatedly like cron:

```bash
PYTHONPATH=backend:scripts python scripts/run_ingest_scheduler.py --interval-seconds 1800
```

To backfill every currently reachable track through Music2Emo:

```bash
PYTHONPATH=backend python scripts/run_music2emo_backfill.py \
  --preview-limit 100 \
  --inference-limit 25 \
  --all
```

6. Run dbt manually when needed:

```bash
cd dbt
/opt/anaconda3/envs/ve/bin/dbt run --profiles-dir . --select staging intermediate
/opt/anaconda3/envs/ve/bin/dbt snapshot --profiles-dir .
/opt/anaconda3/envs/ve/bin/dbt run --profiles-dir . --select marts
/opt/anaconda3/envs/ve/bin/dbt test --profiles-dir .
```

7. Start the API:

```bash
PYTHONPATH=backend uvicorn app.main:app --reload --port 8000
```

8. Start the frontend:

```bash
cd frontend
npm install
npm run dev
```

The dashboard runs at `http://localhost:3000` and calls the FastAPI backend at `http://localhost:8000`.

## Music2Emo Notes

Music2Emo is run as a worker job, not inside FastAPI request handlers. The worker downloads iTunes previews, converts them to WAV with `ffmpeg`, runs the model from `MUSIC2EMO_REPO_PATH`, and stores results in `raw.track_emotion_features`.

The model writes:

- raw valence/arousal
- normalized `valence` and `energy`
- app mood label
- predicted mood tags
- inference timing
- failure messages for tracks with no preview or failed inference

The pipeline records per-track inference time in `raw.track_emotion_features.inference_seconds`. After the first full run, use this query to inspect observed performance:

```sql
select avg(inference_seconds) as avg_seconds_per_track
from raw.track_emotion_features
where inference_seconds is not null;
```

If average inference is slow, lower `MUSIC2EMO_INFERENCE_LIMIT` so each scheduled tick stays manageable.

## Optional Privacy Mode

The frontend shows real listening counts by default:

```bash
VITE_HIDE_REAL_NUMBERS=false
```

If you ever want screenshots or demos without exact counts, set:

```bash
VITE_HIDE_REAL_NUMBERS=true
```

When enabled, the UI masks count labels and flattens count-based chart/bar sizing. The database and API still use real values.

## Quality Gate

Airflow calls `app.quality.sql_checks.run_quality_gate` before dbt transforms. The gate checks:

- required raw recent-track fields
- no future `played_at`
- raw weather required fields and temperature sanity range
- `dim_tracks.mood_confidence` between 0 and 1
- `dim_tracks.mood_label` in the configured mood set
- mood null rate below `MOOD_NULL_RATE_THRESHOLD`

The matching Great Expectations suite definitions live in `great_expectations/expectations`.

## Airflow

DAGs live in `airflow/dags`:

- `lastfm_ingest_dag`: every 30 minutes
- `weather_ingest_dag`: nightly at 2 AM
- `mood_classification_dag`: waits for Last.fm ingestion, refreshes dbt track models, fetches iTunes previews, runs Music2Emo, then refreshes mood models
- `data_quality_dag`: waits for mood classification
- `dbt_transform_dag`: waits for the quality gate

Backfill dbt for a range:

```bash
airflow dags trigger dbt_transform_dag --conf '{"start_date": "2026-02-01", "end_date": "2026-02-28"}'
```

The dbt DAG accepts the conf shape above; individual models can read `var('start_date')` and `var('end_date')` as date-range filters when incremental backfill scoping is needed.

## Snowflake Migration

Use `dbt/profiles.yml.example` as the starting point for the Snowflake target. Migration steps:

1. Create Snowflake warehouse, database, and schema.
2. Fill Snowflake env vars in `.env`.
3. Seed or copy raw data into Snowflake.
4. Run `dbt run --target snowflake`.
5. Run `dbt test --target snowflake`.
6. Point Airflow and FastAPI at the Snowflake-backed schema.
7. Compare `/api/stats/overview?period=all` against the PostgreSQL baseline.

PostgreSQL-specific raw JSON handling is isolated in dbt macros under `dbt/macros`.

## Breaking Schema Change Simulation

When simulating a breaking raw schema change, document:

- the changed raw column or constraint
- updated dbt source/staging models
- whether a backfill was required
- API/frontend impact
- validation results after `dbt test`
