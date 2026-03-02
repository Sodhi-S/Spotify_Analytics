# Product Requirements Document (PRD)

## Spotify Listening Intelligence Platform

**Author:** Sahej Singh Sodhi
**Created:** March 2, 2026
**Status:** Draft
**Version:** 0.1

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
11. [Infrastructure & Deployment](#11-infrastructure--deployment)
12. [Data Quality & Observability](#12-data-quality--observability)
13. [Timeline](#13-timeline)
14. [Cost Estimate](#14-cost-estimate)
15. [Resume Bullet](#15-resume-bullet)
16. [Open Questions](#16-open-questions)

---

## 1. Overview

The Spotify Listening Intelligence Platform is a production-grade data engineering project that ingests personal Spotify listening data (and supplementary weather data), transforms it through a modeled data warehouse, enforces data quality gating, orchestrates pipelines with Airflow, and surfaces insights through a FastAPI backend and React/TypeScript frontend dashboard.

The project mirrors a core data engineering workflow: **multi-source API ingestion with incremental loading, dimensional modeling with dbt, orchestrated pipelines with Airflow, and data quality gating with Great Expectations** — all on real, continuously flowing data. The React frontend serves as the demo/presentation layer; the engineering is underneath it.

---

## 2. Goals & Objectives

### Primary Goal

Build an end-to-end data engineering platform using real Spotify listening data that demonstrates production-grade DE skills across ingestion, modeling, quality, orchestration, and serving.

### Specific Objectives

| Objective | Success Criteria |
| --- | --- |
| Reliable incremental data ingestion | Data flows cleanly for 3+ consecutive days before advancing past Phase 1 |
| Dimensional data modeling | Star schema with staging → intermediate → marts layers, all models tested |
| Multi-source data joining | Weather data joined with listening data via date dimension |
| Data quality enforcement | Great Expectations gates dbt runs; failures alert to Slack |
| Pipeline orchestration | Airflow DAGs with sensors, backfill support, and secret management |
| Analytics-ready API | FastAPI endpoints query pre-aggregated dbt mart tables |
| Visual dashboard | React frontend with heatmap, trend lines, mood clusters, and radar chart |
| Containerized deployment | Docker Compose for local dev; Railway/EC2 + Vercel for production |

---

## 3. Target User

- **Phase 1–4:** Single user (the developer) — personal Spotify account data ingested via cron job. OAuth is used only for the developer's own token management.
- **Phase 5+:** Multi-user support via Spotify OAuth flow, allowing other users to authenticate and view their own dashboards. This introduces per-user ingestion and a multi-tenant data model.

---

## 4. Tech Stack

| Layer | Technology |
| --- | --- |
| **Ingestion** | Python, Spotify API, Open-Meteo API |
| **Orchestration** | Apache Airflow |
| **Transformation** | dbt Core |
| **Data Quality** | Great Expectations |
| **Warehouse** | PostgreSQL (local, Phases 1–6) → Snowflake (prod, Phase 7) |
| **Backend API** | FastAPI |
| **Frontend** | React + TypeScript, Recharts, D3 |
| **Infrastructure** | Docker Compose, AWS EC2, Vercel |

---

## 5. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Apache Airflow (Orchestration)                │
│                                                                      │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────────┐  │
│  │ spotify_ingest   │  │ weather_ingest    │  │ data_quality_dag   │  │
│  │ _dag (30 min)    │  │ _dag (nightly)    │  │ (GE checks)        │  │
│  └───────┬─────────┘  └───────┬──────────┘  └────────┬───────────┘  │
│          │                    │                       │              │
│          ▼                    ▼                       ▼              │
│  ┌─────────────────────────────────────┐   ┌────────────────────┐   │
│  │     PostgreSQL / Snowflake          │   │  dbt_transform_dag │   │
│  │                                     │   │  (sensor-triggered)│   │
│  │  raw schema  →  staging  →  marts   │◄──┤                    │   │
│  └──────────────────┬──────────────────┘   └────────────────────┘   │
│                     │                                                │
└─────────────────────┼────────────────────────────────────────────────┘
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
1. Airflow triggers ingestion scripts on schedule (Spotify every 30 min, weather nightly).
2. Raw data lands in PostgreSQL `raw` schema.
3. Great Expectations validates raw data; dbt runs only if validation passes.
4. dbt transforms data through staging → intermediate → mart layers (star schema).
5. FastAPI reads from pre-aggregated mart tables.
6. React frontend consumes FastAPI endpoints.

---

## 6. Data Sources

### 6.1 Spotify API

| Endpoint | Data | Frequency |
| --- | --- | --- |
| `GET /me/player/recently-played` | Listening history (50 track limit per call) | Every 30 minutes |
| `GET /audio-features/{id}` | Energy, valence, danceability, tempo, acousticness, speechiness, instrumentalness | On new track discovery |
| `GET /artists/{id}` | Genres, popularity, follower count | On new artist discovery |

### 6.2 Open-Meteo Weather API (Free)

| Data | Frequency |
| --- | --- |
| Daily weather for user's city — temperature (°C), precipitation, weather code | Nightly |

**Join Strategy:** Weather data joins with `fact_listens` via `dim_dates` to enable analysis such as: *"Do you listen to sadder music on rainy days?"*

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
| `date_id` | FK → dim_dates | |
| `played_at` | TIMESTAMP | |
| `ms_played` | INTEGER | Milliseconds played |

**Deduplication Key:** `played_at` + `track_id` composite key.

#### Dimension Tables

**`dim_tracks`**

| Column | Type |
| --- | --- |
| `track_id` | PK |
| `name` | VARCHAR |
| `album` | VARCHAR |
| `release_date` | DATE |
| `energy` | FLOAT |
| `valence` | FLOAT |
| `danceability` | FLOAT |
| `tempo` | FLOAT |
| `acousticness` | FLOAT |
| `speechiness` | FLOAT |
| `instrumentalness` | FLOAT |

**`dim_artists`** *(SCD Type 2)*

| Column | Type | Notes |
| --- | --- | --- |
| `artist_id` | PK | |
| `name` | VARCHAR | |
| `genres` | VARCHAR/ARRAY | |
| `popularity` | INTEGER | Tracked over time via SCD Type 2 |
| `follower_count` | INTEGER | Tracked over time via SCD Type 2 |

**`dim_dates`**

| Column | Type |
| --- | --- |
| `date_id` | PK |
| `hour` | INTEGER |
| `day_of_week` | VARCHAR |
| `month` | INTEGER |
| `is_weekend` | BOOLEAN |

**`dim_weather`**

| Column | Type |
| --- | --- |
| `date_id` | PK / FK → dim_dates |
| `city` | VARCHAR |
| `temp_c` | FLOAT |
| `precipitation` | FLOAT |
| `weather_code` | INTEGER |

#### Pre-Aggregated Mart

**`mart_listening_summary`** — Pre-aggregated table so API queries stay fast. Exact aggregation granularity TBD based on endpoint needs (likely daily/weekly rollups of listen counts, average audio features, top tracks/artists).

---

## 8. Phase Breakdown & Requirements

### Phase 1: Data Ingestion Foundation | Week 1

**Goal:** Get data flowing reliably before touching anything else.

#### Requirements

| ID | Requirement | Priority |
| --- | --- | --- |
| P1-1 | Implement Spotify OAuth authentication and token refresh | Must |
| P1-2 | Ingest from `GET /me/player/recently-played` (50 track limit) | Must |
| P1-3 | Ingest from `GET /audio-features/{id}` for each track | Must |
| P1-4 | Ingest from `GET /artists/{id}` for each artist | Must |
| P1-5 | Incremental loading logic using `last_fetched_at` timestamp stored in DB | Must |
| P1-6 | Deduplication on `played_at` + `track_id` composite key | Must |
| P1-7 | Dead letter queue — failed/malformed API records go to `raw_failed` table | Must |
| P1-8 | Retry logic with exponential backoff on API failures | Must |
| P1-9 | Slack webhook alert when ingestion fails or returns 0 rows unexpectedly | Must |
| P1-10 | Cron job running every 30 minutes | Must |

#### Exit Criteria

- Data is flowing cleanly for **3+ consecutive days** before moving to Phase 2.

---

### Phase 2: Data Modeling with dbt | Week 2

**Goal:** Transform raw JSON into a clean, analytics-ready star schema.

#### Requirements

| ID | Requirement | Priority |
| --- | --- | --- |
| P2-1 | dbt models for each layer: staging → intermediate → marts | Must |
| P2-2 | dbt tests on every model — `not_null`, `unique`, `accepted_values`, `relationships` | Must |
| P2-3 | Slowly Changing Dimension (SCD Type 2) on `dim_artists` to track popularity changes over time | Must |
| P2-4 | `mart_listening_summary` pre-aggregated table for fast API queries | Must |
| P2-5 | `dbt docs generate` to produce lineage documentation | Must |
| P2-6 | Include lineage screenshot in project README | Should |

---

### Phase 3: Second Data Source + Quality Gating | Week 3

**Goal:** Add a second unrelated data source and enforce data quality before dbt runs.

#### Requirements — Weather Ingestion

| ID | Requirement | Priority |
| --- | --- | --- |
| P3-1 | Pull daily weather for user's city from Open-Meteo API (temperature, precipitation, weather code) | Must |
| P3-2 | Join weather with `fact_listens` in dbt via `dim_dates` | Must |
| P3-3 | Enable analysis: "Do you listen to sadder music on rainy days?" | Must |

#### Requirements — Great Expectations Quality Gating

| ID | Requirement | Priority |
| --- | --- | --- |
| P3-4 | Assert audio features are always between 0 and 1 | Must |
| P3-5 | Assert `played_at` is never in the future | Must |
| P3-6 | Assert row counts are within expected range (flag if 0 rows ingested) | Must |
| P3-7 | Gate the Airflow DAG so dbt only runs if GE validation passes | Must |
| P3-8 | Failed GE runs log to Slack | Must |

---

### Phase 4: Airflow Orchestration | Week 4

**Goal:** Make the pipeline production-grade with proper scheduling, monitoring, and backfill support.

#### DAG Design

| DAG | Schedule | Description |
| --- | --- | --- |
| `spotify_ingest_dag` | Every 30 min | Hits Spotify API, loads to raw schema |
| `weather_ingest_dag` | Nightly | Pulls daily weather data |
| `dbt_transform_dag` | After ingest succeeds | Triggered via Airflow sensor |
| `data_quality_dag` | Before dbt runs | Runs GE checks, sends Slack alert on failure |

#### Requirements

| ID | Requirement | Priority |
| --- | --- | --- |
| P4-1 | Implement all four DAGs as specified above | Must |
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
| P5-1 | `GET /api/stats/overview` — total listens, unique artists, top genres | Must |
| P5-2 | `GET /api/top-tracks` — top N tracks by time period | Must |
| P5-3 | `GET /api/audio-features/trends` — avg energy/valence/etc by week or month | Must |
| P5-4 | `GET /api/listening/heatmap` — listen counts by hour × day_of_week | Must |
| P5-5 | `GET /api/moods/clusters` — K-Means cluster results with track metadata | Nice to Have |
| P5-6 | `GET /api/weather-correlation` — listening mood vs weather conditions | Must |
| P5-7 | `GET /auth/spotify` — OAuth flow initiation for multi-user support | Must |
| P5-8 | `GET /auth/callback` — OAuth token exchange for multi-user support | Must |

---

### Phase 6: React Frontend | Weeks 5–6

**Goal:** Build a compelling live demo of the pipeline working.

#### Four Core Views

| View | Description | Chart Library |
| --- | --- | --- |
| **Overview** | Total stats, top 5 tracks/artists, sonic fingerprint radar chart (avg audio features) | Recharts |
| **Listening Heatmap** | GitHub-style grid of hour × day_of_week — shows morning vs night listener patterns | D3 |
| **Taste Over Time** | Line charts of avg energy, valence, danceability by month — musical evolution | Recharts |
| **Mood Clusters** *(Nice to Have)* | K-Means scatter plot by audio features, hover to see track names | Recharts |

#### Requirements

| ID | Requirement | Priority |
| --- | --- | --- |
| P6-1 | Implement Overview, Listening Heatmap, and Taste Over Time views | Must |
| P6-2 | Implement Mood Clusters view (K-Means scatter plot) | Nice to Have |
| P6-3 | Use Recharts for line/bar/radar charts | Must |
| P6-4 | Use D3 for the heatmap (Recharts handles it poorly) | Must |
| P6-5 | TypeScript interfaces matching API response shapes | Must |
| P6-6 | Clean, well-structured component architecture | Should |

---

### Phase 7: Snowflake Migration + Docker + Deployment | Week 6

**Goal:** Migrate the warehouse to Snowflake, containerize, and deploy the full stack.

#### Requirements

| ID | Requirement | Priority |
| --- | --- | --- |
| P7-1 | Migrate warehouse from PostgreSQL to Snowflake — update dbt profiles, validate all models run cleanly | Must |
| P7-2 | Docker Compose wires together Postgres (or Snowflake connection), Airflow, FastAPI — one command spins everything up | Must |
| P7-3 | Deploy backend to Railway (free tier) or AWS EC2 (free tier, 12 months) | Must |
| P7-4 | Deploy frontend to Vercel (free tier) | Must |
| P7-5 | Point cron job at the deployed backend URL | Must |

---

## 9. API Specification

| Method | Endpoint | Description | Response Summary |
| --- | --- | --- | --- |
| GET | `/api/stats/overview` | Dashboard overview stats | Total listens, unique artists, top genres |
| GET | `/api/top-tracks` | Top tracks by time period | List of tracks with play counts, accepts time period param |
| GET | `/api/audio-features/trends` | Audio feature trends | Avg energy, valence, danceability, etc. by week/month |
| GET | `/api/listening/heatmap` | Listening heatmap data | Matrix of listen counts: hour (0–23) × day_of_week (Mon–Sun) |
| GET | `/api/moods/clusters` | Mood clustering results *(Nice to Have)* | K-Means cluster assignments with track metadata |
| GET | `/api/weather-correlation` | Weather vs mood correlation | Listening mood metrics alongside weather conditions |
| GET | `/auth/spotify` | Initiate Spotify OAuth | Redirects to Spotify authorization |
| GET | `/auth/callback` | OAuth callback handler | Exchanges code for access/refresh tokens |

---

## 10. Frontend Views

### 10.1 Overview Dashboard

- Total listens count
- Unique artists count
- Top 5 tracks
- Top 5 artists
- Sonic fingerprint radar chart (average audio features: energy, valence, danceability, tempo, acousticness, speechiness, instrumentalness)

### 10.2 Listening Heatmap

- GitHub-style contribution grid
- X-axis: Day of week (Mon–Sun)
- Y-axis: Hour of day (0–23)
- Color intensity: Listen count
- Immediately reveals morning vs. night listening patterns

### 10.3 Taste Over Time

- Line charts showing monthly averages
- Tracked features: energy, valence, danceability
- Shows musical evolution over time

### 10.4 Mood Clusters *(Nice to Have)*

- K-Means scatter plot
- Axes: Audio features (specific features TBD — likely energy vs. valence or first two principal components)
- Hover interaction: Shows track name and metadata
- Color-coded by cluster assignment

---

## 11. Infrastructure & Deployment

### Local Development

- **Docker Compose** orchestrates: PostgreSQL, Airflow (webserver + scheduler + worker), FastAPI
- Single `docker-compose up` spins up the entire stack

### Production

| Component | Platform | Tier |
| --- | --- | --- |
| Backend (FastAPI) | Railway or AWS EC2 | Free |
| Frontend (React) | Vercel | Free |
| Database | PostgreSQL (Phases 1–6) → Snowflake (Phase 7, prod) | Free / $400 free credits |
| Airflow | Docker on EC2 or local | Free |

---

## 12. Data Quality & Observability

### Great Expectations Checks

| Check | Target |
| --- | --- |
| Audio features between 0 and 1 | `dim_tracks.energy`, `valence`, `danceability`, `acousticness`, `speechiness`, `instrumentalness` |
| `played_at` is never in the future | `fact_listens.played_at` |
| Row count within expected range | All ingestion tables |

### Alerting

- **Slack webhooks** for:
  - Ingestion failures
  - Ingestion returning 0 rows unexpectedly
  - Great Expectations validation failures

### dbt Testing

- `not_null` on all required columns
- `unique` on primary keys
- `accepted_values` where applicable
- `relationships` for foreign key integrity

### Documentation

- `dbt docs generate` for full lineage documentation
- README documentation of breaking schema change simulation and resolution

---

## 13. Timeline

| Week | Phase | Deliverables |
| --- | --- | --- |
| **Week 1** | Phase 1: Data Ingestion Foundation | Spotify OAuth + incremental ingestion + dead letter queue running for 3+ days |
| **Week 2** | Phase 2: Data Modeling with dbt | Star schema with tests, SCD Type 2, lineage docs |
| **Week 3** | Phase 3: Second Source + Quality Gating | Weather API join + Great Expectations quality gating |
| **Week 4** | Phase 4: Airflow Orchestration | Airflow DAGs with sensors, backfill logic, schema change handling |
| **Week 5** | Phase 5: FastAPI Backend | API endpoints + Spotify OAuth for multi-user support |
| **Weeks 5–6** | Phase 6: React Frontend | Heatmap, trends, radar chart (mood clusters if time permits) |
| **Week 6** | Phase 7: Snowflake Migration + Docker + Deployment | PostgreSQL → Snowflake migration, Docker Compose + Railway/EC2 + Vercel deployment |

**Total Duration:** ~6 weeks

---

## 14. Cost Estimate

| Resource | Cost |
| --- | --- |
| Spotify API | Free |
| Open-Meteo API | Free |
| PostgreSQL (local) | Free |
| dbt Core | Free (open source) |
| Airflow (Docker) | Free |
| Great Expectations | Free (open source) |
| Railway (backend) | Free tier |
| Vercel (frontend) | Free tier |
| Snowflake (optional) | $400 free credits on signup |
| **Total (Months 1–2)** | **~$0** |

---

## 15. Resume Bullet

> Built a production-grade Spotify analytics platform with incremental Python ingestion pipelines (30-min cron), multi-source dbt star schema modeling (Spotify + weather APIs), Great Expectations quality gating, Airflow orchestration with backfill support, PostgreSQL → Snowflake warehouse migration, and a FastAPI + React/TypeScript dashboard with audio feature trend analysis.

---

## 16. Resolved Questions

These items were initially ambiguous in the roadmap and have been clarified:

### Q1: Single-User → Multi-User Transition ✅

**Decision:** Phases 1–4 are single-user only (developer's personal account). Multi-user support kicks in at Phase 5 when the OAuth flow is built. This means:
- Phase 1–4 ingestion uses the developer's own Spotify credentials via cron.
- Phase 5 introduces `GET /auth/spotify` and `GET /auth/callback` to allow other users to authenticate and view their own dashboards.
- The data model and ingestion pipeline will need to become user-aware (per-user data isolation) starting in Phase 5.

### Q2: Snowflake Migration Timing ✅

**Decision:** PostgreSQL is the warehouse for Phases 1–6 (all local development and initial deployment). The migration to Snowflake happens in **Phase 7** alongside Docker + deployment. This means:
- dbt models should be written with warehouse portability in mind where practical (avoid Postgres-only SQL where possible).
- Phase 7 includes updating `dbt profiles.yml` to target Snowflake and validating all models run cleanly on Snowflake.

### Q3: K-Means Clustering ✅

**Decision:** K-Means mood clustering is a **nice-to-have** feature, not a core requirement. The `/api/moods/clusters` endpoint and the Mood Clusters frontend view are deprioritized. If implemented, implementation details (where the model runs, recomputation frequency, feature selection) will be decided at that time.

---

*This PRD is a living document and will be updated as implementation progresses.*
