# Music Listening Intelligence Platform

<div align="center">
  <br />
  <p>
    <strong>End-to-end music analytics built with Last.fm, Music2Emo, dbt, FastAPI, and React.</strong>
  </p>
  <p>
    <img src="https://img.shields.io/badge/Python-Data%20Pipelines-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python Data Pipelines" />
    <img src="https://img.shields.io/badge/dbt-Analytics%20Engineering-FF694B?style=for-the-badge&logo=dbt&logoColor=white" alt="dbt Analytics Engineering" />
    <img src="https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI Backend" />
    <img src="https://img.shields.io/badge/React-Dashboard-61DAFB?style=for-the-badge&logo=react&logoColor=black" alt="React Dashboard" />
  </p>
</div>

<p align="center">
Music Listening Intelligence transforms personal Last.fm scrobble history into a production-style analytics platform. It ingests listening and weather data, enriches tracks with ML-powered mood features from audio previews, models the data with dbt, validates quality, and serves insights through a FastAPI + React dashboard.
</p>

---

## The Problem

Music listening data is rich, but most personal dashboards only answer simple questions like "What were my top artists?" or "What did I play the most?" They rarely show how listening behavior changes by time, mood, artist profile, or external context such as weather.

The engineering problem is more interesting than a chart alone. A useful music intelligence platform needs reliable ingestion, incremental loading, enrichment, transformation, validation, and a clean application layer over analytics-ready tables.

This project exists to turn raw scrobbles into a complete data product: source data lands in a raw schema, ML jobs generate mood features, dbt builds dimensional models and marts, quality checks protect downstream metrics, and a typed dashboard exposes the results.

---

## How It Works

Music Listening Intelligence runs through five connected pipelines: listening ingestion, weather ingestion, image enrichment, mood classification, and warehouse transformation. Each pipeline is designed so raw data remains reproducible while the dashboard reads only modeled outputs.

### Pipeline Architecture

```mermaid
flowchart TB
    subgraph sources [External Sources]
        LASTFM[Last.fm API]
        WEATHER[Open-Meteo API]
        ITUNES[iTunes Search API]
    end

    subgraph ingestion [Python Ingestion Jobs]
        TRACKS[Recent Tracks]
        TAGS[Track and Artist Tags]
        ARTISTS[Artist Metadata]
        WEATHER_JOB[Weather by City]
        PREVIEW_LOOKUP[Audio Preview Lookup]
        IMAGE_LOOKUP[Artwork Enrichment]
    end

    subgraph raw [PostgreSQL Raw Schema]
        RAW_TRACKS[(raw.recent_tracks)]
        RAW_TAGS[(raw.track_tags and raw.artist_tags)]
        RAW_ARTISTS[(raw.artists)]
        RAW_WEATHER[(raw.weather)]
        RAW_IMAGES[(raw image enrichments)]
        RAW_EMOTION[(raw.track_emotion_features)]
        RAW_FAILED[(raw.raw_failed)]
    end

    subgraph mood [Music2Emo Worker]
        DOWNLOAD[Download Preview]
        CONVERT[Convert to WAV]
        INFERENCE[Run Music2Emo]
        SCORE[Persist Valence, Energy, Mood]
    end

    subgraph transform [dbt Transformation Layer]
        STAGING[Staging Models]
        INTERMEDIATE[Intermediate Models]
        SNAPSHOTS[SCD Type 2 Artist Snapshot]
        MARTS[Fact, Dimension, and Mart Tables]
    end

    subgraph quality [Quality Layer]
        SQL_GATE[SQL Quality Gate]
        DBT_TESTS[dbt Tests]
        GE[Great Expectations Suites]
    end

    subgraph app [Application Layer]
        API[FastAPI]
        UI[React and TypeScript Dashboard]
    end

    LASTFM --> TRACKS --> RAW_TRACKS
    LASTFM --> TAGS --> RAW_TAGS
    LASTFM --> ARTISTS --> RAW_ARTISTS
    WEATHER --> WEATHER_JOB --> RAW_WEATHER
    ITUNES --> IMAGE_LOOKUP --> RAW_IMAGES
    ITUNES --> PREVIEW_LOOKUP --> DOWNLOAD --> CONVERT --> INFERENCE --> SCORE --> RAW_EMOTION

    RAW_TRACKS --> SQL_GATE
    RAW_WEATHER --> SQL_GATE
    SQL_GATE --> STAGING

    RAW_TRACKS --> STAGING
    RAW_TAGS --> STAGING
    RAW_ARTISTS --> STAGING
    RAW_WEATHER --> STAGING
    RAW_IMAGES --> STAGING
    RAW_EMOTION --> STAGING

    STAGING --> INTERMEDIATE --> MARTS
    STAGING --> SNAPSHOTS --> MARTS
    MARTS --> DBT_TESTS
    RAW_TRACKS --> GE
    RAW_WEATHER --> GE
    MARTS --> API --> UI
```

### Listening Ingestion

The listening pipeline uses Last.fm as the system of record for music history. It collects recent scrobbles, track tags, artist metadata, artist tags, and chart snapshots. Raw records are written to PostgreSQL with dedupe keys, source metadata, and failed-record capture through `raw.raw_failed`.

The same ingestion code can run once for local development or on an interval through the local scheduler.

### Mood Classification

The mood pipeline scores tracks from audio previews instead of relying on deprecated Spotify audio features. It searches iTunes for preview URLs, downloads the available previews, converts them to WAV with `ffmpeg`, and runs Music2Emo inference in a worker job.

Music2Emo outputs raw valence/arousal, normalized `valence` and `energy`, app-level mood labels, predicted mood tags, inference timing, and failure messages. Results are stored in `raw.track_emotion_features` and joined into dbt models downstream.

### Weather Correlation

Open-Meteo supplies daily weather for the configured city. The warehouse models temperature, precipitation, weather category, season, weekend flags, and date-level weather summaries.

The dashboard uses this layer to compare listening volume, mood, tags, and artist behavior across weather categories and temperature buckets.

### Warehouse Modeling

dbt turns raw source tables into analytics-ready models through staging, intermediate, snapshot, and mart layers.

The modeled warehouse includes `fact_listens`, `dim_tracks`, `dim_artists`, `dim_dates`, `dim_weather`, `mart_listening_summary`, and `mart_tag_listen_counts`. Artist metadata is tracked with an SCD Type 2 snapshot so changes over time can be preserved instead of overwritten.

### Dashboard Experience

The React dashboard reads from FastAPI instead of connecting directly to the database. It includes overview metrics, top tracks, mood fingerprints, weather correlations, and settings for changing the weather location.

The frontend also includes an optional privacy mode that hides exact listening counts while keeping the API and database unchanged.

---

## System Architecture

The project follows a monorepo structure with clear separation between ingestion, transformation, backend services, and frontend views.

```mermaid
flowchart TB
    subgraph storage [Data Storage]
        POSTGRES[(PostgreSQL)]
        SNOWFLAKE[(Snowflake Migration Target)]
    end

    subgraph modeling [Transform and Validate]
        DBT[dbt Core]
        SQL_CHECKS[Executable SQL Checks]
        DBT_TESTS[dbt Tests]
        EXPECTATIONS[Great Expectations]
    end

    subgraph backend [Backend Server]
        FASTAPI[FastAPI]
        subgraph services [Service Layer]
            OVERVIEW[Overview Service]
            TOP_TRACKS[Top Tracks Service]
            MOODS[Artist Mood Fingerprints]
            WEATHER_SERVICE[Weather Correlation Service]
            SETTINGS[Settings Service]
        end
        SCHEMAS[Pydantic Schemas]
        SQLALCHEMY[SQLAlchemy and psycopg]
    end

    subgraph frontend [Browser Client]
        REACT[React]
        TYPESCRIPT[TypeScript]
        VITE[Vite]
        RECHARTS[Recharts]
        VIEWS[Overview, Top Tracks, Moods, Weather, Settings]
    end

    POSTGRES --> DBT --> POSTGRES
    DBT -. optional target .-> SNOWFLAKE
    DBT --> DBT_TESTS
    POSTGRES --> EXPECTATIONS

    POSTGRES --> SQLALCHEMY --> FASTAPI
    FASTAPI --> OVERVIEW
    FASTAPI --> TOP_TRACKS
    FASTAPI --> MOODS
    FASTAPI --> WEATHER_SERVICE
    FASTAPI --> SETTINGS
    FASTAPI --> SCHEMAS

    REACT --> VITE
    REACT --> TYPESCRIPT
    REACT --> RECHARTS
    REACT --> VIEWS
    VIEWS <-->|REST API| FASTAPI
```

### Frontend Architecture

The frontend is built with React and TypeScript using Vite for local development and builds. Dashboard views are separated into focused components for overview metrics, ranked lists, top tracks, mood analysis, weather correlation, settings, and shared visualization elements.

The UI consumes typed API responses defined in `frontend/src/types.ts`. This keeps frontend rendering aligned with the Pydantic models exposed by FastAPI and makes the dashboard easier to evolve as new analytics views are added.

### Backend Architecture

The backend follows a route-service-schema structure. FastAPI defines endpoint contracts, Pydantic schemas validate response shapes, and service classes encapsulate SQL queries against modeled warehouse tables.

The API surface includes:

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Service health check |
| `GET /api/stats/overview` | Total listens, unique tracks/artists, top tracks, top artists, top tags, and mood breakdown |
| `GET /api/top-tracks` | Ranked track details with play counts, tags, images, and mood fields |
| `GET /api/moods/artist-fingerprints` | Artist-level mood profiles and insight callouts |
| `GET /api/weather-correlation` | Weather, temperature, season, mood, and listening correlations |
| `GET /api/settings` | Current app settings |
| `PUT /api/settings` | Update weather location and refresh weather data |
| `GET /api/cities` | North America city search backed by Open-Meteo geocoding |

Interactive API docs are available at `http://localhost:8000/docs` when the backend is running.

### Data Layer

PostgreSQL stores both raw source data and dbt-modeled analytics tables for local development. Raw tables preserve source-aligned records, while dbt models create the clean warehouse layer consumed by the application.

The dbt project also includes a Snowflake profile template at `dbt/profiles.yml.example`. PostgreSQL-specific raw JSON behavior is isolated in dbt macros to make a future Snowflake migration more direct.

---

## Technical Implementation

### Incremental Ingestion and Failure Capture

The ingestion layer is built around repeatable jobs that can safely run many times. Recent-track ingestion deduplicates scrobbles, enrichment jobs only process newly discovered or incomplete entities, and failures are captured separately so a bad API response does not poison the modeled warehouse.

Raw tables include listening events, track tags, artist tags, artist metadata, weather data, image enrichments, and Music2Emo outputs. This separation makes it possible to re-run transformations without re-fetching every source.

### ML Feature Engineering

Mood classification runs as a batch worker rather than a request-time API operation. This keeps the dashboard fast and prevents expensive audio inference from blocking user interactions.

The worker performs preview lookup, audio conversion, inference, normalization, and persistence. Missing previews are recorded with error details so full backfills do not retry the same unavailable tracks forever. Batch limits such as `MUSIC2EMO_PREVIEW_LIMIT` and `MUSIC2EMO_INFERENCE_LIMIT` keep scheduled runs predictable.

### dbt Modeling

The dbt project is organized into layered models:

| Layer | Examples | Purpose |
| --- | --- | --- |
| Staging | `stg_recent_tracks`, `stg_artists`, `stg_weather` | Clean and standardize raw source tables |
| Intermediate | `int_listens_enriched`, `int_weather_enriched` | Join source domains and prepare analytics logic |
| Snapshots | `artists_snapshot` | Preserve changing artist metadata over time |
| Marts | `fact_listens`, `dim_tracks`, `dim_artists`, `dim_dates`, `dim_weather` | Serve analytics queries |
| Summary Marts | `mart_listening_summary`, `mart_tag_listen_counts` | Power dashboard-level aggregations |

### Data Quality

The quality layer checks both raw inputs and modeled outputs. The executable SQL gate validates required fields, future timestamps, weather sanity ranges, mood confidence bounds, accepted mood labels, and mood null-rate thresholds.

dbt tests enforce uniqueness, not-null constraints, relationships, and accepted values across warehouse models. Great Expectations suite definitions live in `great_expectations/expectations` for additional validation coverage.

### Privacy Mode

The dashboard can mask exact listening counts for screenshots or demos:

```text
VITE_HIDE_REAL_NUMBERS=true
```

When enabled, the UI hides count labels and flattens count-based chart sizing. The database and API continue using real values.

---

## Tech Stack

| Layer | Technology |
| --- | --- |
| Ingestion | Python, Requests, Last.fm API, Open-Meteo API, iTunes Search API |
| ML Feature Engineering | Music2Emo, Torch, Librosa, ffmpeg |
| Storage | PostgreSQL 16 |
| Transformation | dbt Core, dbt-postgres, dbt-snowflake |
| Data Quality | SQL checks, dbt tests, Great Expectations |
| Scheduling | Local Python scheduler |
| Backend API | FastAPI, Pydantic, SQLAlchemy, psycopg |
| Frontend | React, TypeScript, Vite, Recharts |
| Local Infrastructure | Docker Compose |
| Configuration | `.env`, `python-dotenv` |

---

## Local Setup

### Prerequisites

- Python 3.10+
- Node.js 18+ and npm
- Docker Desktop
- PostgreSQL client tools such as `psql`
- Last.fm API key and username
- Optional: Conda for the Music2Emo worker environment

### 1. Start PostgreSQL

```bash
docker compose up -d postgres
```

Initialize the raw schema:

```bash
bash scripts/db_init.sh
```

Check database status:

```bash
bash scripts/db_status.sh
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Fill the required values:

```text
LASTFM_API_KEY=your_lastfm_api_key
LASTFM_USERNAME=your_lastfm_username
DB_CONNECTION_STRING=postgresql+psycopg://postgres:postgres@localhost:5432/music_intelligence
OPENMETEO_CITY=Toronto
```

### 3. Install Python Dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

If you use the existing Conda workflow from the runbooks:

```bash
conda activate ve
python -m pip install -r backend/requirements.txt
python -m pip install -r requirements-dbt.txt
```

### 4. Run One Pipeline Tick

```bash
PYTHONPATH=backend:scripts python scripts/run_ingest_once.py
```

This command ingests Last.fm data, refreshes dbt track models, looks up previews, runs Music2Emo when enabled, writes mood outputs, rebuilds listening models, and ingests weather data.

Run repeatedly like cron:

```bash
PYTHONPATH=backend:scripts python scripts/run_ingest_scheduler.py --interval-seconds 1800
```

### 5. Run dbt Manually

```bash
cd dbt
dbt debug --profiles-dir .
dbt run --profiles-dir . --select staging intermediate
dbt snapshot --profiles-dir .
dbt run --profiles-dir . --select marts
dbt test --profiles-dir .
cd ..
```

If your local dbt executable lives in the `ve` Conda environment:

```bash
cd dbt
/opt/anaconda3/envs/ve/bin/dbt run --profiles-dir . --select staging intermediate
/opt/anaconda3/envs/ve/bin/dbt snapshot --profiles-dir .
/opt/anaconda3/envs/ve/bin/dbt run --profiles-dir . --select marts
/opt/anaconda3/envs/ve/bin/dbt test --profiles-dir .
cd ..
```

### 6. Start the Backend

```bash
PYTHONPATH=backend uvicorn app.main:app --reload --port 8000
```

Verify:

```bash
curl http://localhost:8000/health
curl "http://localhost:8000/api/stats/overview?period=30d"
```

### 7. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

The dashboard runs at `http://localhost:3000` and calls the API at `http://localhost:8000`.

---

## Music2Emo Setup

Music2Emo uses a separate worker-friendly environment because audio dependencies are more sensitive than the dashboard API dependencies.

```bash
conda create -n music2emo python=3.10
conda activate music2emo
conda install ffmpeg -c conda-forge
pip install -r requirements-music2emo.txt
git clone https://github.com/AMAAI-Lab/Music2Emotion /tmp/Music2Emotion
```

Set these in `.env`:

```text
MUSIC2EMO_REPO_PATH=/tmp/Music2Emotion
MUSIC2EMO_MODEL_WEIGHTS=/tmp/Music2Emotion/saved_models/J_all.ckpt
MUSIC2EMO_RUN_AFTER_INGEST=true
MUSIC2EMO_PREVIEW_LIMIT=100
MUSIC2EMO_INFERENCE_LIMIT=25
```

Run a small test backfill:

```bash
PYTHONPATH=backend python scripts/run_music2emo_backfill.py \
  --preview-limit 10 \
  --inference-limit 3
```

Backfill all currently reachable tracks:

```bash
PYTHONPATH=backend python scripts/run_music2emo_backfill.py \
  --preview-limit 100 \
  --inference-limit 25 \
  --all
```

Manual Apple Music/iTunes overrides can be stored in:

```text
data/manual_itunes_overrides.csv
```

Apply overrides:

```bash
PYTHONPATH=backend python scripts/apply_itunes_overrides.py
```

More detail is available in `docs/runbook-music2emo.md`.

---

## Project Structure

```text
Spotify_Analytics/
|-- backend/
|   |-- app/
|   |   |-- api/                    # Pydantic schemas
|   |   |-- core/                   # Settings and alerts
|   |   |-- ingestion/              # Last.fm, Open-Meteo, iTunes clients
|   |   |-- pipeline/               # Pipeline job helpers
|   |   |-- quality/                # SQL quality gate
|   |   |-- services/               # Dashboard query services
|   |   |-- db.py                   # Database connection helper
|   |   `-- main.py                 # FastAPI app
|   `-- sql/                        # Raw schema and migrations
|-- dbt/
|   |-- macros/                     # Cross-warehouse helpers
|   |-- models/
|   |   |-- staging/
|   |   |-- intermediate/
|   |   `-- marts/
|   `-- snapshots/                  # SCD Type 2 snapshots
|-- docs/
|   |-- FRDs/                       # Feature requirement documents
|   |-- PRD/                        # Product requirements
|   `-- runbook-*.md                # Local and Music2Emo runbooks
|-- frontend/
|   `-- src/
|       |-- components/             # Dashboard views and UI components
|       |-- api.ts                  # API client
|       |-- types.ts                # Shared response types
|       `-- App.tsx                 # Main dashboard shell
|-- great_expectations/
|   `-- expectations/               # Validation suite definitions
|-- scripts/                        # Pipeline, db, backfill, and audit commands
|-- docker-compose.yml              # Local PostgreSQL service
`-- README.md
```

---

## Incoming Features

1. Datetime analysis
2. Generate playlist
3. Exports

---

## Documentation

- `docs/PRD/prd.md`: product goals, architecture, data sources, and scope.
- `docs/runbook-local-app.md`: local app setup and daily workflow.
- `docs/runbook-music2emo.md`: Music2Emo setup, backfills, overrides, and troubleshooting.
- `docs/FRDs/`: feature requirements for the pipeline, dashboard, top tracks, moods, weather, and related views.
- `great_expectations/expectations/`: Great Expectations validation suites.

---

## Current Scope

This is a local-first analytics platform for one Last.fm account and one configurable weather location. The current implementation focuses on data engineering depth: ingestion, enrichment, ML feature generation, modeling, quality, API serving, and dashboarding.

Multi-user authentication, hosted deployment, and real-time streaming analytics are outside the current scope. The dbt project includes a Snowflake-ready profile to support a future warehouse migration.
