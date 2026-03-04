# Product Requirements Document (PRD)

## Music Listening Intelligence Platform

**Author:** Sahej Singh Sodhi
**Created:** March 2, 2026
**Status:** Draft
**Version:** 0.3

---

## Changelog

| Version | Change |
| --- | --- |
| 0.1 | Initial draft — Spotify API as primary data source |
| 0.2 | Removed deployment and multi-user scope |
| 0.3 | Pivoted from Spotify to Last.fm — Spotify deprecated audio features and preview_url in Feb 2026. Replaced audio feature columns with ML-computed mood classification via a Librosa-trained model. |

---

## Table of Contents

1. [Overview](#1-overview)
2. [Goals & Objectives](#2-goals--objectives)
3. [Target User](#3-target-user)
4. [Tech Stack](#4-tech-stack)
5. [Architecture Overview](#5-architecture-overview)
6. [Data Sources](#6-data-sources)
7. [Data Model](#7-data-model)
8. [Phase Breakdown & Requirements](#8-phase-breakdown--requirements)
9. [API Specification](#9-api-specification)
10. [Frontend Views](#10-frontend-views)
11. [Local Infrastructure](#11-local-infrastructure)
12. [Data Quality & Observability](#12-data-quality--observability)
13. [Timeline](#13-timeline)
14. [Cost Estimate](#14-cost-estimate)
15. [Resume Bullet](#15-resume-bullet)
16. [Resolved Questions](#16-resolved-questions)

---

## 1. Overview

The Music Listening Intelligence Platform is a production-grade data engineering project that ingests personal listening data from Last.fm, runs ML-based mood classification on track audio using a Librosa-trained model, transforms everything through a modeled data warehouse, enforces data quality gating, orchestrates pipelines with Airflow, and surfaces insights through a FastAPI backend and React/TypeScript frontend dashboard.

The project mirrors a core data engineering workflow: **multi-source API ingestion with incremental loading, ML feature engineering inside the pipeline, dimensional modeling with dbt, orchestrated pipelines with Airflow, and data quality gating with Great Expectations** — all on real, continuously flowing data.

**Why Last.fm over Spotify:** Spotify deprecated `GET /audio-features`, `GET /audio-analysis`, and `preview_url` in February 2026, removing the core data that made Spotify analytically interesting. Last.fm's API is free, stable, has no equivalent deprecations, and stores complete scrobble history with no 50-track polling limit.

---

## 2. Goals & Objectives

### Primary Goal

Build an end-to-end data engineering platform using real listening data that demonstrates production-grade DE skills across ingestion, ML feature engineering, modeling, quality, orchestration, and serving.

### Specific Objectives

| Objective | Success Criteria |
| --- | --- |
| Reliable incremental data ingestion | Data flows cleanly for 3+ consecutive days before advancing past Phase 1 |
| ML mood classification in pipeline | Librosa model runs on track audio previews, mood_label populated for all tracks with available audio |
| Dimensional data modeling | Star schema with staging → intermediate → marts layers, all models tested |
| Multi-source data joining | Weather data joined with listening data via date dimension |
| Data quality enforcement | Great Expectations gates dbt runs; failures alert to Slack |
| Pipeline orchestration | Airflow DAGs with sensors, backfill support, and secret management |
| Analytics-ready API | FastAPI endpoints query pre-aggregated dbt mart tables |
| Visual dashboard | React frontend with heatmap, mood trends, taste evolution, and radar chart |
| Containerized local dev | Docker Compose spins up the full local stack with one command |

---

## 3. Target User

**Single user (the developer)** throughout all phases. This is a personal analytics platform built on the developer's own Last.fm scrobble history. Last.fm API requires only an API key for read access to public scrobble data — no OAuth needed for single-user personal use.

Multi-user support is explicitly out of scope for this version.

**Setup prerequisite:** Connect your Spotify account to Last.fm at last.fm/settings so every Spotify play automatically scrobbles to Last.fm. This is a free Last.fm feature and must be done before Phase 1 to begin accumulating data.

---

## 4. Tech Stack

| Layer | Technology |
| --- | --- |
| **Ingestion** | Python, Last.fm API, Open-Meteo API |
| **ML Feature Engineering** | Librosa-trained mood classification model (happy, sad, angry, etc.) |
| **Audio Source** | iTunes Preview API (30-second previews for mood model input) |
| **Orchestration** | Apache Airflow |
| **Transformation** | dbt Core |
| **Data Quality** | Great Expectations |
| **Warehouse** | PostgreSQL (Phases 1–6) → Snowflake (Phase 7) |
| **Backend API** | FastAPI |
| **Frontend** | React + TypeScript, Recharts, D3 |
| **Infrastructure** | Docker Compose (local only) |
| **Secret Management** | `.env` + `python-dotenv` |

---

## 5. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Apache Airflow (Orchestration)                  │
│                                                                         │
│  ┌──────────────────┐  ┌─────────────────┐  ┌──────────────────────┐   │
│  │ lastfm_ingest    │  │ weather_ingest   │  │ data_quality_dag     │   │
│  │ _dag (30 min)    │  │ _dag (nightly)   │  │ (GE checks)          │   │
│  └───────┬──────────┘  └───────┬─────────┘  └──────────┬───────────┘   │
│          │                     │                        │               │
│          ▼                     ▼                        ▼               │
│  ┌───────────────────────────────────────┐   ┌──────────────────────┐  │
│  │        PostgreSQL / Snowflake         │   │  dbt_transform_dag   │  │
│  │                                       │   │  (sensor-triggered)  │  │
│  │  raw schema  →  staging  →  marts     │◄──┤                      │  │
│  └────────────────────┬──────────────────┘   └──────────────────────┘  │
│                       │                                                 │
│  ┌────────────────────▼──────────────────┐                             │
│  │         mood_classification_dag        │                             │
│  │  iTunes preview → Librosa model →      │                             │
│  │  mood_label written to dim_tracks      │                             │
│  └───────────────────────────────────────┘                             │
└──────────────────────────────────────────────────────────────────────┬─┘
                                                                       │
                                                                       ▼
                                                               ┌───────────────┐
                                                               │   FastAPI      │
                                                               │   Backend      │
                                                               └───────┬───────┘
                                                                       │
                                                                       ▼
                                                               ┌───────────────┐
                                                               │  React + TS   │
                                                               │  Frontend     │
                                                               └───────────────┘
```

**Data Flow:**
1. Airflow triggers Last.fm ingestion every 30 min, weather ingestion nightly.
2. Raw data lands in PostgreSQL `raw` schema.
3. Great Expectations validates raw data; dbt runs only if validation passes.
4. dbt transforms data through staging → intermediate → mart layers.
5. Separately, `mood_classification_dag` fetches iTunes audio previews for new tracks, runs the Librosa model, and writes `mood_label` + `mood_confidence` back to `dim_tracks`.
6. FastAPI reads from pre-aggregated mart tables.
7. React frontend consumes FastAPI endpoints.

---

## 6. Data Sources

### 6.1 Last.fm API

Base URL: `https://ws.audioscrobbler.com/2.0/`

All requests use: `?method=<method>&api_key=<key>&format=json`

| Method | Replaces | Data | Frequency |
| --- | --- | --- | --- |
| `user.getRecentTracks` | `GET /me/player/recently-played` | Full scrobble history, paginated, no 50-track limit | Every 30 minutes |
| `track.getTopTags` | `GET /audio-features/{id}` | Community tags per track (e.g. melancholic, energetic, chill) | On new track discovery |
| `artist.getInfo` | `GET /artists/{id}` | Artist metadata, listener count, play count, similar artists, tags | On new artist discovery |
| `artist.getTopTags` | — | Community genre tags per artist | On new artist discovery |
| `user.getTopArtists` | — | Top artists by time period | Daily |
| `user.getTopTracks` | — | Top tracks by time period | Daily |

**Auth:** API key only — no OAuth required for reading public scrobble data. Store in `.env`.

**Rate limit:** 5 requests per second averaged over a 5-minute period. Well within project needs.

### 6.2 iTunes Preview API (Audio for Mood Model)

Base URL: `https://itunes.apple.com/search`

| Data | Frequency |
| --- | --- |
| 30-second AAC audio preview per track, fetched by searching artist + track name | On new track discovery |

**Auth:** None required — completely free and open.

**Rate limit:** ~20 calls per minute. The `mood_classification_dag` must throttle requests accordingly — batch new tracks and space requests to stay within this limit.

**Track matching logic:** iTunes does not use Last.fm or Spotify track IDs. Tracks are matched by text search using artist name + track name as a query string. A confidence check must be applied to the returned result before accepting it:

```python
def get_itunes_preview(artist, track):
    results = search_itunes(f"{artist} {track}")
    if not results:
        return None

    top_result = results[0]
    returned_artist = top_result["artistName"].lower()

    # Reject if returned artist doesn't match
    if artist.lower() not in returned_artist:
        return None

    return top_result.get("previewUrl")
```

If the match fails the confidence check, `preview_url` stays `NULL` and mood classification is skipped for that track.

**Known matching failure cases:**
- Featuring artists (e.g. "Drake ft. Future" vs "Drake")
- Special characters or accents in track names
- Cover songs returning wrong artist
- Regional availability differences
- Minor title differences (e.g. "Nothin'" vs "Nothing")

**Terms of Service note:** Apple intends preview URLs for promotional display purposes. Using them for ML audio processing is a grey area. For a personal portfolio project running locally this is acceptable in practice, but worth noting.

**Fallback:** If no iTunes preview is found or the match fails, `mood_label` and `mood_confidence` are set to `NULL`. dbt tests assert null rates stay within acceptable thresholds.

### 6.3 Open-Meteo Weather API

| Data | Frequency |
| --- | --- |
| Daily weather for user's city — temperature (°C), precipitation, weather code | Nightly |

**Join Strategy:** Weather joins with `fact_listens` via `dim_dates` on calendar date.

---

### 6.4 Librosa Mood Classification Model

The mood classification model is a pre-trained Librosa-based model provided by the developer. It is not trained as part of this project — it is loaded and run as an inference step inside the pipeline.

**Model file location:** `model/mood_classifier.pkl` in the project root. Committed to the repo (or documented in README if too large for version control).

**Input format:**
- 30-second AAC audio file downloaded from iTunes Preview API
- Resampled to a standard sample rate (exact rate TBD based on model requirements — document in README)
- Converted to a numpy array before being passed to the model

**Output format:**
- A single predicted mood label (e.g. `happy`, `sad`, `angry`, `calm`, `energetic`, `melancholic`)
- A probability distribution across all mood classes — the highest probability is used as `mood_confidence`

```python
# Example inference pseudocode
import librosa
import pickle

model = pickle.load(open("model/mood_classifier.pkl", "rb"))

def classify_mood(preview_path):
    y, sr = librosa.load(preview_path, sr=TARGET_SAMPLE_RATE)
    features = extract_features(y, sr)  # MFCCs or other Librosa features
    probabilities = model.predict_proba([features])[0]
    mood_label = model.classes_[probabilities.argmax()]
    mood_confidence = probabilities.max()
    return mood_label, mood_confidence
```

**Mood classes:** 6+ classes (exact labels TBD — document in README once confirmed). All valid mood labels must be added to a dbt `accepted_values` test on `dim_tracks.mood_label`.

**Confidence derivation:** `mood_confidence` is the max class probability from `model.predict_proba()`. Ranges from 0 to 1.

**Batch processing:** The model runs only on tracks where `mood_label IS NULL` and `preview_url IS NOT NULL` — already-classified tracks are skipped.

**Performance note:** Document inference time per track in README. If inference takes more than a few seconds per track, consider async processing or running the DAG less frequently than ingestion.

---

## 7. Data Model

### Star Schema Design

#### Fact Table

**`fact_listens`**

| Column | Type | Notes |
| --- | --- | --- |
| `listen_id` | PK | Surrogate key |
| `track_id` | FK → dim_tracks | |
| `artist_id` | FK → dim_artists | |
| `date_id` | FK → dim_dates | Calendar date only (YYYY-MM-DD) |
| `played_at` | TIMESTAMP | Full timestamp stored on fact table |
| `hour` | INTEGER | Hour of listen (0–23), stored on fact for heatmap queries |
| `ms_played` | INTEGER | Milliseconds played — enables skip detection and full-listen analysis |

**Deduplication Key:** `played_at` + `track_id` composite key.

**Note on date granularity:** `date_id` maps to a calendar date so `fact_listens` joins cleanly to `dim_weather`, which is daily. Hour is stored directly on `fact_listens` for heatmap analysis.

#### Dimension Tables

**`dim_tracks`**

| Column | Type | Source | Notes |
| --- | --- | --- | --- |
| `track_id` | PK | Last.fm | |
| `name` | VARCHAR | Last.fm | |
| `album` | VARCHAR | Last.fm | |
| `release_date` | DATE | Last.fm | |
| `top_tags` | ARRAY | Last.fm `track.getTopTags` | Community tags e.g. melancholic, chill, energetic |
| `preview_url` | VARCHAR | iTunes Search API | 30-second preview URL used as Librosa model input |
| `mood_label` | VARCHAR | Librosa ML model | ML-computed classification: happy, sad, angry, etc. NULL if no iTunes preview available |
| `mood_confidence` | FLOAT | Librosa ML model | Model confidence score (0–1). NULL if mood_label is NULL |
| `mood_energy` | FLOAT | Derived from mood_label | *(Future — see OQ1)* Numeric proxy score mapped from mood_label. Not implemented until OQ1 is resolved. |
| `mood_valence` | FLOAT | Derived from mood_label | *(Future — see OQ1)* Numeric proxy score mapped from mood_label. Not implemented until OQ1 is resolved. |

**`dim_artists`** *(SCD Type 2)*

| Column | Type | Notes |
| --- | --- | --- |
| `artist_id` | PK | |
| `name` | VARCHAR | |
| `genres` | ARRAY | Last.fm top tags used as genre proxy |
| `listener_count` | INTEGER | Tracked over time via SCD Type 2 |
| `play_count` | INTEGER | Tracked over time via SCD Type 2 |
| `valid_from` | DATE | SCD Type 2 effective date |
| `valid_to` | DATE | SCD Type 2 expiry date (NULL = current) |
| `is_current` | BOOLEAN | Convenience flag for current record |

**`dim_dates`**

| Column | Type |
| --- | --- |
| `date_id` | PK (YYYY-MM-DD) |
| `day_of_week` | VARCHAR |
| `month` | INTEGER |
| `year` | INTEGER |
| `is_weekend` | BOOLEAN |

**`dim_weather`**

| Column | Type |
| --- | --- |
| `date_id` | FK → dim_dates |
| `city` | VARCHAR |
| `temp_c` | FLOAT |
| `precipitation` | FLOAT |
| `weather_code` | INTEGER |

#### Pre-Aggregated Mart

**`mart_listening_summary`** — Pre-aggregated daily/weekly rollups of listen counts, mood distributions, and top tags. Exact granularity finalized during Phase 2 based on endpoint needs.

---

## 8. Phase Breakdown & Requirements

### Phase 1: Data Ingestion Foundation | Week 1

**Goal:** Get data flowing reliably from Last.fm before touching anything else.

**Setup prerequisite before coding:** Connect Spotify to Last.fm at last.fm/settings to begin scrobbling.

#### Requirements

| ID | Requirement | Priority |
| --- | --- | --- |
| P1-1 | Generate Last.fm API key and store in `.env` using `python-dotenv` | Must |
| P1-2 | Ingest from `user.getRecentTracks` with pagination support | Must |
| P1-3 | Ingest from `track.getTopTags` for each new track | Must |
| P1-4 | Ingest from `artist.getInfo` and `artist.getTopTags` for each new artist | Must |
| P1-5 | Incremental loading logic using `last_fetched_at` timestamp stored in DB | Must |
| P1-6 | Deduplication on `played_at` + `track_id` composite key | Must |
| P1-7 | Dead letter queue — failed/malformed API records go to `raw_failed` table | Must |
| P1-8 | Retry logic with exponential backoff on API failures | Must |
| P1-9 | Respect Last.fm rate limit of 5 req/sec — implement request throttling | Must |
| P1-10 | Slack webhook alert when ingestion fails or returns 0 rows unexpectedly | Must |
| P1-11 | Cron job running every 30 minutes | Must |

#### Exit Criteria

Data is flowing cleanly for **3+ consecutive days** before moving to Phase 2.

---

### Phase 2: Data Modeling with dbt | Week 2

**Goal:** Transform raw Last.fm data into a clean, analytics-ready star schema.

#### Requirements

| ID | Requirement | Priority |
| --- | --- | --- |
| P2-1 | dbt models for each layer: staging → intermediate → marts | Must |
| P2-2 | dbt tests on every model — `not_null`, `unique`, `accepted_values`, `relationships` | Must |
| P2-3 | SCD Type 2 on `dim_artists` tracking listener_count and play_count over time | Must |
| P2-4 | `mart_listening_summary` pre-aggregated table for fast API queries | Must |
| P2-5 | `dbt docs generate` to produce lineage documentation | Must |
| P2-6 | Include lineage screenshot in project README | Should |
| P2-7 | Handle NULL `mood_label` gracefully in all downstream models | Must |

---

### Phase 3: ML Mood Classification + Weather + Quality Gating | Week 3

**Goal:** Add mood classification pipeline, weather data source, and data quality gating.

#### Requirements — Mood Classification Pipeline

| ID | Requirement | Priority |
| --- | --- | --- |
| P3-1 | For each new track with `mood_label IS NULL` and `preview_url IS NOT NULL`, query iTunes Search API using artist + track name | Must |
| P3-2 | Apply confidence check on iTunes search result — reject if returned artist doesn't match | Must |
| P3-3 | Download matched AAC preview file and resample to model's required sample rate | Must |
| P3-4 | Extract Librosa features and run `mood_classifier.pkl` inference | Must |
| P3-5 | Write `mood_label` (predicted class) and `mood_confidence` (max class probability) to `dim_tracks` | Must |
| P3-6 | If no iTunes preview found or match fails confidence check, set `mood_label = NULL`, `mood_confidence = NULL` | Must |
| P3-7 | Run mood classification as a separate Airflow DAG (`mood_classification_dag`) | Must |
| P3-8 | Respect iTunes rate limit of ~20 calls/minute — implement request throttling in DAG | Must |
| P3-9 | Document model inference time per track and target sample rate in README | Must |

#### Requirements — Weather Ingestion

| ID | Requirement | Priority |
| --- | --- | --- |
| P3-10 | Pull daily weather for user's city from Open-Meteo API | Must |
| P3-11 | Join weather with `fact_listens` in dbt via `dim_dates` on calendar date | Must |
| P3-12 | Enable analysis: "Do you listen to sadder music on rainy days?" | Must |

#### Requirements — Great Expectations Quality Gating

| ID | Requirement | Priority |
| --- | --- | --- |
| P3-13 | Assert `mood_confidence` is between 0 and 1 when not NULL | Must |
| P3-14 | Assert `played_at` is never in the future | Must |
| P3-15 | Assert row counts are within expected range (flag if 0 rows ingested) | Must |
| P3-16 | Assert NULL rate of `mood_label` stays below acceptable threshold (TBD) | Must |
| P3-17 | Assert `mood_label` only contains valid model classes (dbt `accepted_values` test) | Must |
| P3-18 | Gate the Airflow DAG so dbt only runs if GE validation passes | Must |
| P3-19 | Failed GE runs log to Slack | Must |

---

### Phase 4: Airflow Orchestration | Week 4

**Goal:** Make the pipeline production-grade with proper scheduling, monitoring, and backfill support.

#### DAG Design

| DAG | Schedule | Description |
| --- | --- | --- |
| `lastfm_ingest_dag` | Every 30 min | Hits Last.fm API, loads to raw schema |
| `weather_ingest_dag` | Nightly | Pulls daily weather data |
| `mood_classification_dag` | After ingest | Fetches iTunes previews, runs Librosa model, updates dim_tracks |
| `dbt_transform_dag` | After mood classification succeeds | Triggered via Airflow sensor |
| `data_quality_dag` | Before dbt runs | Runs GE checks, sends Slack alert on failure |

#### Requirements

| ID | Requirement | Priority |
| --- | --- | --- |
| P4-1 | Implement all five DAGs as specified above | Must |
| P4-2 | Backfill logic — ability to re-process any date range if a transformation changes | Must |
| P4-3 | Task dependencies and sensors between DAGs | Must |
| P4-4 | Airflow Variables for config (API keys, DB connection strings) — no hardcoded secrets | Must |
| P4-5 | Simulate a breaking schema change mid-project | Must |
| P4-6 | Document how the schema change was handled in the README | Must |

---

### Phase 5: FastAPI Backend | Week 5

**Goal:** Serve dbt-modeled data to the frontend via a clean REST API.

#### Design Principle

Each endpoint queries **pre-aggregated dbt mart tables** — keep query logic in dbt, not in FastAPI.

#### Requirements

| ID | Requirement | Priority |
| --- | --- | --- |
| P5-1 | `GET /api/stats/overview` — total listens, unique artists, top tags | Must |
| P5-2 | `GET /api/top-tracks` — top N tracks by time period | Must |
| P5-3 | `GET /api/mood/trends` — mood label distribution by week or month | Must |
| P5-4 | `GET /api/listening/heatmap` — listen counts by hour × day_of_week | Must |
| P5-5 | `GET /api/mood/by-time` — mood distribution by hour of day and day of week | Must |
| P5-6 | `GET /api/weather-correlation` — mood distribution vs weather conditions | Must |
| P5-7 | `GET /api/tags/evolution` — how your top community tags shift over time | Must |
| P5-8 | `GET /api/moods/clusters` — mood cluster scatter plot data | Nice to Have |

---

### Phase 6: React Frontend | Weeks 5–6

**Goal:** Build a compelling live demo of the pipeline working.

#### Four Core Views

| View | Description | Chart Library |
| --- | --- | --- |
| **Overview** | Total listens, unique artists, top tags, mood breakdown donut chart | Recharts |
| **Listening Heatmap** | GitHub-style grid of hour × day_of_week | D3 |
| **Mood Over Time** | Stacked area chart of mood label distribution by month | Recharts |
| **Mood vs Weather** | Scatter or bar chart correlating mood with weather conditions | Recharts |

#### Requirements

| ID | Requirement | Priority |
| --- | --- | --- |
| P6-1 | Implement all four core views | Must |
| P6-2 | Mood cluster scatter plot view | Nice to Have |
| P6-3 | Use Recharts for all charts except heatmap | Must |
| P6-4 | Use D3 for the heatmap | Must |
| P6-5 | TypeScript interfaces matching API response shapes | Must |
| P6-6 | Clean, well-structured component architecture | Should |

---

### Phase 7: Snowflake Migration | Week 6

**Goal:** Migrate the local warehouse from PostgreSQL to Snowflake and validate all models run cleanly.

#### Requirements

| ID | Requirement | Priority |
| --- | --- | --- |
| P7-1 | Sign up for Snowflake free trial ($400 credits, no credit card required) | Must |
| P7-2 | Update `dbt profiles.yml` to target Snowflake | Must |
| P7-3 | Validate all dbt models run cleanly on Snowflake | Must |
| P7-4 | Update Airflow connection strings to point at Snowflake | Must |
| P7-5 | Validate FastAPI endpoints still return correct data | Must |
| P7-6 | Document migration steps and any SQL changes required in README | Should |

**Note:** Write dbt models with warehouse portability in mind throughout Phases 1–6 — avoid Postgres-specific SQL where possible.

---

## 9. API Specification

| Method | Endpoint | Description | Response Summary |
| --- | --- | --- | --- |
| GET | `/api/stats/overview` | Dashboard overview | Total listens, unique artists, top community tags, mood breakdown donut data |
| GET | `/api/top-tracks` | Top tracks by time period | Tracks with play counts, mood labels, and top tags. Accepts `period` param (7day, 1month, 3month, 6month, 12month) |
| GET | `/api/mood/trends` | Mood distribution over time | Mood label counts by week or month — powers the stacked area chart |
| GET | `/api/listening/heatmap` | Heatmap data | Matrix of listen counts: hour (0–23) × day_of_week (Mon–Sun) |
| GET | `/api/mood/by-time` | Mood by time of day and day of week | Mood distribution broken down by hour and day of week |
| GET | `/api/weather-correlation` | Mood vs weather conditions | Mood label distribution alongside daily weather — answers "do you listen to sadder music on rainy days?" |
| GET | `/api/tags/evolution` | Community tag trends over time | Top Last.fm community tags ranked by month — shows genre and style evolution |
| GET | `/api/moods/clusters` | Cluster scatter data *(Nice to Have)* | Mood cluster assignments with track metadata for scatter plot |

---

## 10. Frontend Views

### 10.1 Overview Dashboard

- Total listens count
- Unique artists count
- Top 5 tracks and artists
- Top community tags
- Mood breakdown donut chart showing distribution across all mood classes

### 10.2 Listening Heatmap

- GitHub-style contribution grid
- X-axis: Day of week (Mon–Sun)
- Y-axis: Hour of day (0–23)
- Color intensity: Listen count

### 10.3 Mood Over Time

- Stacked area chart
- X-axis: Month
- Y-axis: Proportion of listens per mood class
- Shows how your emotional listening profile evolves over time

### 10.4 Mood vs Weather

- Bar or scatter chart correlating mood label distribution with weather conditions
- Answers: "Do you listen to sadder music on rainy days?"

---

## 11. Local Infrastructure

Everything runs locally via Docker Compose. No deployment in scope for this version.

### Docker Compose Services

| Service | Notes |
| --- | --- |
| PostgreSQL | Primary warehouse for Phases 1–6 |
| Airflow (webserver + scheduler + worker) | Local orchestration |
| FastAPI | Runs on `localhost:8000` |
| React (dev server) | Runs on `localhost:3000` |

### Secret Management

All credentials stored in `.env` using `python-dotenv`. `.env` is gitignored. A `.env.example` with placeholder values is committed to the repo.

```
LASTFM_API_KEY=your_key_here
LASTFM_USERNAME=your_username_here
OPENMETEO_CITY=Toronto
SLACK_WEBHOOK_URL=your_webhook_here
DB_CONNECTION_STRING=postgresql://localhost:5432/music_intelligence
```

---

## 12. Data Quality & Observability

### Great Expectations Checks

| Check | Target |
| --- | --- |
| `mood_confidence` between 0 and 1 when not NULL | `dim_tracks.mood_confidence` |
| `played_at` is never in the future | `fact_listens.played_at` |
| Row counts within expected range | All ingestion tables |
| NULL rate of `mood_label` below threshold | `dim_tracks.mood_label` |
| `mood_label` only contains valid model classes | `dim_tracks.mood_label` (accepted_values = exact class list from model) |
| iTunes rate limit respected — no more than 20 requests/minute | `mood_classification_dag` task logs |

### Alerting

- **Slack webhooks** for ingestion failures, 0-row ingestion, GE validation failures, mood classification failures

### dbt Testing

- `not_null` on all required columns
- `unique` on primary keys
- `accepted_values` where applicable
- `relationships` for foreign key integrity

### Documentation

- `dbt docs generate` for full lineage documentation
- README documents breaking schema change simulation and resolution
- `.env.example` committed documenting all required environment variables

---

## 13. Timeline

| Week | Phase | Deliverables |
| --- | --- | --- |
| **Week 1** | Phase 1: Data Ingestion Foundation | Last.fm ingestion + incremental loading + dead letter queue running for 3+ days |
| **Week 2** | Phase 2: Data Modeling with dbt | Star schema with tests, SCD Type 2, lineage docs |
| **Week 3** | Phase 3: ML + Weather + Quality Gating | Mood classification pipeline + weather join + Great Expectations gating |
| **Week 4** | Phase 4: Airflow Orchestration | Five DAGs with sensors, backfill logic, schema change handling |
| **Week 5** | Phase 5: FastAPI Backend | API endpoints serving pre-aggregated mart data |
| **Weeks 5–6** | Phase 6: React Frontend | Heatmap, mood trends, mood vs weather, overview |
| **Week 6** | Phase 7: Snowflake Migration | PostgreSQL → Snowflake migration, all models validated |

---

## 14. Cost Estimate

| Resource | Cost |
| --- | --- |
| Last.fm API | Free |
| iTunes Preview API | Free |
| Open-Meteo API | Free |
| PostgreSQL (local) | Free |
| dbt Core | Free (open source) |
| Airflow (Docker) | Free |
| Great Expectations | Free (open source) |
| Snowflake (Phase 7) | $400 free credits on signup, no credit card required |
| **Total (Months 1–2)** | **~$0** |

---

## 15. Resume Bullet

> blank for now

---

## 16. Resolved Questions

### Q1: Single-User Only ✅

**Decision:** Single-user project throughout. Last.fm API requires only an API key for public scrobble data — no OAuth needed.

### Q2: No Deployment in Scope ✅

**Decision:** Project runs entirely locally. Docker Compose is the only infrastructure requirement. Deployment deferred to a future iteration.

### Q3: Snowflake Migration Timing ✅

**Decision:** PostgreSQL for Phases 1–6. Snowflake migration in Phase 7. Write dbt models with portability in mind throughout.

### Q4: K-Means Clustering ✅

**Decision:** Nice-to-have, not a core requirement. Deprioritized. Mood classification from the Librosa model replaces the need for unsupervised clustering.

### Q5: Date Granularity in Data Model ✅

**Decision:** `date_id` maps to calendar date (YYYY-MM-DD) so `fact_listens` joins cleanly to `dim_weather`. Hour stored directly on `fact_listens`.

### Q6: Spotify → Last.fm Pivot ✅

**Decision:** Spotify deprecated `GET /audio-features`, `GET /audio-analysis`, and `preview_url` in February 2026. Last.fm is the replacement — free, stable, no equivalent deprecations, full scrobble history with no polling limits.

### Q7: Audio Features → ML Mood Classification ✅

**Decision:** Spotify's pre-computed audio features (energy, valence, danceability) are replaced by a Librosa-trained mood classification model. iTunes Preview API provides 30-second audio clips as model input. `mood_label` (e.g. happy, sad, angry) and `mood_confidence` replace all float audio feature columns in `dim_tracks`. Tracks without an iTunes preview get `NULL` for both fields.

### Q8: NULL Handling for mood_label ✅

**Decision:** Tracks without an available iTunes audio preview have `mood_label = NULL` and `mood_confidence = NULL`. dbt tests assert the NULL rate stays within an acceptable threshold (exact threshold TBD during Phase 3). All downstream models and API endpoints handle NULLs gracefully.

---

## 17. Open Questions

### OQ1: Mood-to-Numeric Proxy Scores ⏳

**Question:** Should `mood_label` be mapped to numeric proxy scores (e.g. `mood_energy`, `mood_valence`) to enable richer analytics like averages, trend lines, and scatter plots?

**Context:** The current data model only has `mood_label` (categorical) and `mood_confidence` (a single float). This means `/api/moods/clusters` has no numeric axes to plot — a scatter plot requires at least two numeric dimensions. One solution is a static mapping like:

```python
mood_to_energy = {
    "happy":  0.8,
    "angry":  0.9,
    "calm":   0.3,
    "sad":    0.2,
}
```

This would unlock averages, trend lines, and the clusters scatter plot, but introduces a manually-defined mapping that may oversimplify the model's output.

**Decision:** Deferred. Revisit after Phase 3 when real mood classification data is available and the distribution of mood labels across the dataset is known. If mood labels are rich and well-distributed, numeric proxies are worth adding. If the distribution is skewed or sparse, the mapping may not be meaningful.

**Impact if resolved yes:** Add `mood_energy` and `mood_valence` columns to `dim_tracks`. Update `/api/moods/clusters` endpoint. Enables scatter plot in React frontend.

---

*This PRD is a living document and will be updated as implementation progresses.*
