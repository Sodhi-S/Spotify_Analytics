# Music Listening Intelligence Platform

Local data engineering project for Last.fm scrobbles, iTunes preview-based mood classification, dbt marts, quality gates, Airflow orchestration, and a FastAPI + React overview dashboard.

## What Is Implemented

- Last.fm ingestion jobs for recent tracks, track tags, artist info, artist tags, and user chart snapshots.
- Open-Meteo daily weather ingestion.
- iTunes preview lookup with artist-confidence matching and Librosa model inference staging.
- Raw PostgreSQL schema with incremental metadata, dedupe keys, and `raw.raw_failed`.
- dbt staging, intermediate, mart, and SCD Type 2 artist snapshot models.
- Executable SQL quality gate plus Great Expectations suite definitions.
- Airflow DAGs for Last.fm, weather, mood classification, data quality, and dbt transforms.
- `GET /api/stats/overview` FastAPI endpoint.
- React/TypeScript overview view with period selector, stat cards, top lists, and mood donut chart.

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

4. Run ingestion jobs locally:

```bash
PYTHONPATH=backend python -c "from app.pipeline.lastfm_jobs import run_lastfm_ingestion; print(run_lastfm_ingestion())"
PYTHONPATH=backend python -c "from app.pipeline.weather_jobs import fetch_daily_weather; print(fetch_daily_weather())"
```

5. Run dbt:

```bash
cd dbt
/opt/anaconda3/envs/ve/bin/dbt run --profiles-dir . --select staging intermediate
/opt/anaconda3/envs/ve/bin/dbt snapshot --profiles-dir .
/opt/anaconda3/envs/ve/bin/dbt run --profiles-dir . --select marts
/opt/anaconda3/envs/ve/bin/dbt test --profiles-dir .
```

6. Start the API:

```bash
PYTHONPATH=backend uvicorn app.main:app --reload --port 8000
```

7. Start the frontend:

```bash
cd frontend
npm install
npm run dev
```

The overview dashboard runs at `http://localhost:3000` and calls `http://localhost:8000/api/stats/overview`.

## Mood Model Notes

The inference job expects `model/mood_classifier.pkl` by default. Set `MOOD_MODEL_PATH` to override it.

Current target sample rate: `TARGET_SAMPLE_RATE=22050`.

The pipeline records per-track inference time in `raw.mood_classification_results.inference_seconds`. After the first full run, use this query to document observed performance:

```sql
select avg(inference_seconds) as avg_seconds_per_track
from raw.mood_classification_results
where inference_seconds is not null;
```

If average inference rises above a few seconds per track, run `mood_classification_dag` less frequently or split inference into smaller batches.

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
- `mood_classification_dag`: waits for Last.fm ingestion
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
