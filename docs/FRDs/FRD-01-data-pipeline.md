# FRD-001: Data Pipeline

## Ingestion, ML Mood Classification, Transformation, Quality Gating, Orchestration & Snowflake Migration

**Parent PRD:** [Music Listening Intelligence Platform — PRD v0.3](../PRD/prd.md)
**PRD Phases:** 1, 2, 3, 4, 7
**Author:** Sahej Singh Sodhi
**Created:** March 2, 2026
**Updated:** March 3, 2026
**Status:** Draft

---

## 1. Purpose

This FRD specifies the end-to-end data pipeline: how data enters the system from Last.fm and Open-Meteo APIs, how ML-based mood classification is applied using a Librosa-trained model on iTunes audio previews, how raw data is transformed into an analytics-ready star schema via dbt, how data quality is enforced with Great Expectations, how pipelines are orchestrated with Airflow, and how the warehouse is migrated from PostgreSQL to Snowflake.

---

## 2. Scope

| In Scope | Out of Scope |
| --- | --- |
| Last.fm API ingestion (recent tracks, track tags, artist info, artist tags, top artists, top tracks) | Multi-user ingestion |
| iTunes Preview API integration for mood model input | Deployment / cloud hosting |
| Librosa-based mood classification pipeline | Frontend rendering |
| Open-Meteo weather API ingestion | FastAPI endpoint logic (see feature FRDs) |
| Raw schema design and loading | Training the mood classification model (pre-trained model provided) |
| dbt transformation (staging → intermediate → marts) | |
| Great Expectations data quality checks | |
| Airflow DAG orchestration (5 DAGs) | |
| PostgreSQL → Snowflake migration | |

---

## 3. Data Ingestion

### 3.1 Last.fm Ingestion

#### 3.1.1 Authentication

- API key only — no OAuth required for reading public scrobble data.
- Key stored in `.env` as `LASTFM_API_KEY`.
- Username stored in `.env` as `LASTFM_USERNAME`.

#### 3.1.2 Endpoints & Raw Tables

Base URL: `https://ws.audioscrobbler.com/2.0/`

All requests use: `?method=<method>&api_key=<key>&format=json`

| Last.fm Method | Raw Table | Key Columns Stored | Trigger |
| --- | --- | --- | --- |
| `user.getRecentTracks` | `raw.recent_tracks` | `track_name`, `artist_name`, `album`, `played_at`, `track_mbid`, `artist_mbid` | Every 30 min |
| `track.getTopTags` | `raw.track_tags` | `track_name`, `artist_name`, `tags[]` (name + count) | On new track discovery |
| `artist.getInfo` | `raw.artists` | `artist_name`, `artist_mbid`, `listener_count`, `play_count`, `similar_artists[]`, `bio`, `fetched_at` | On new artist discovery |
| `artist.getTopTags` | `raw.artist_tags` | `artist_name`, `tags[]` (name + count) — used as genre proxy | On new artist discovery |
| `user.getTopArtists` | `raw.top_artists` | `artist_name`, `play_count`, `rank`, `period` | Daily |
| `user.getTopTracks` | `raw.top_tracks` | `track_name`, `artist_name`, `play_count`, `rank`, `period` | Daily |

**Rate limit:** 5 requests per second averaged over a 5-minute period. Implement request throttling to stay within this limit.

#### 3.1.3 Incremental Loading

- A `last_fetched_at` timestamp is persisted in the database (e.g., a `raw.ingestion_metadata` table).
- Each run of `user.getRecentTracks` passes the `from` parameter set to the Unix timestamp of `last_fetched_at` to only fetch new scrobbles.
- Last.fm supports full pagination — no 50-track limit like Spotify. Paginate through all results using `page` parameter.
- After a successful ingestion, `last_fetched_at` is updated to the `played_at` of the most recent record received.

#### 3.1.4 Deduplication

- Before inserting into `raw.recent_tracks`, check for existing rows matching the composite key `(played_at, track_name, artist_name)`.
- Duplicate records are silently skipped.

#### 3.1.5 Dead Letter Queue

- A `raw.raw_failed` table stores records that fail parsing or validation during ingestion.
- Schema: `id`, `source` (e.g., `recent_tracks`, `track_tags`, `artists`), `raw_payload` (JSONB), `error_message`, `failed_at`.
- Records land here when: JSON parsing fails, required fields are missing, or unexpected API response shapes are received.
- Dead letter records are **never** silently dropped — they are always persisted for inspection.

#### 3.1.6 Retry Logic

- API calls use exponential backoff: initial delay 1s, multiplier 2×, max 3 retries.
- After max retries, the record is written to `raw.raw_failed` and the run continues with remaining records.
- If the entire API call fails (e.g., 5xx, network timeout), the run is aborted and a Slack alert is sent.

#### 3.1.7 Slack Alerting

- Webhook URL stored in `.env` as `SLACK_WEBHOOK_URL`.
- Alerts sent on:
  - Ingestion run fails entirely (API down, auth failure).
  - Ingestion returns 0 rows unexpectedly (API returned empty but `last_fetched_at` suggests there should be data).
  - Any records written to `raw.raw_failed`.
- Alert payload includes: timestamp, source, error summary, and count of failed records.

### 3.2 iTunes Preview API (Audio for Mood Model)

#### 3.2.1 API Details

- **Source:** iTunes Search API (free, no auth required).
- **Base URL:** `https://itunes.apple.com/search`
- **Rate limit:** ~20 calls per minute. The `mood_classification_dag` must throttle requests accordingly.

#### 3.2.2 Track Matching Logic

iTunes does not use Last.fm track IDs. Tracks are matched by text search using `artist_name + track_name` as a query string. A confidence check must be applied:

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

#### 3.2.3 Known Matching Failure Cases

- Featuring artists (e.g., "Drake ft. Future" vs "Drake")
- Special characters or accents in track names
- Cover songs returning wrong artist
- Regional availability differences
- Minor title differences (e.g., "Nothin'" vs "Nothing")

#### 3.2.4 Fallback Behavior

If no iTunes preview is found or the match fails the confidence check, `preview_url` stays `NULL` in `dim_tracks` and mood classification is skipped for that track. `mood_label` and `mood_confidence` are set to `NULL`.

### 3.3 Weather Ingestion

#### 3.3.1 API Details

- **Source:** Open-Meteo API (free, no auth required).
- **Endpoint:** `https://api.open-meteo.com/v1/forecast` with `past_days` parameter.
- **Parameters:** latitude/longitude derived from city name (stored in `.env` as `OPENMETEO_CITY`), daily weather variables: `temperature_2m_max`, `precipitation_sum`, `weather_code`.

#### 3.3.2 Raw Table

| Raw Table | Key Columns | Trigger |
| --- | --- | --- |
| `raw.weather` | `date`, `city`, `temp_c`, `precipitation`, `weather_code`, `fetched_at` | Nightly |

#### 3.3.3 Incremental Loading

- Each nightly run fetches weather for the current date (or previous day if run after midnight).
- Deduplication on `date` + `city` — upsert logic (insert if not exists, update if exists).

---

## 4. ML Mood Classification Pipeline

### 4.1 Overview

The mood classification pipeline is a separate Airflow DAG (`mood_classification_dag`) that:
1. Identifies tracks in `dim_tracks` where `mood_label IS NULL` and `preview_url IS NOT NULL`.
2. Downloads 30-second AAC audio previews from iTunes.
3. Runs a pre-trained Librosa-based model to classify each track's mood.
4. Writes `mood_label` and `mood_confidence` back to `dim_tracks`.

### 4.2 Model Details

- **Model file:** `model/mood_classifier.pkl` in the project root.
- **Framework:** scikit-learn classifier trained on Librosa-extracted features.
- **The model is pre-trained and provided by the developer** — it is not trained as part of this project.

### 4.3 Inference Pipeline

```python
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

### 4.4 Output

| Column | Type | Description |
| --- | --- | --- |
| `mood_label` | VARCHAR | Predicted class: e.g., `happy`, `sad`, `angry`, `calm`, `energetic`, `melancholic` |
| `mood_confidence` | FLOAT | Max class probability from `predict_proba()` (0–1) |

### 4.5 Batch Processing Rules

- Only processes tracks where `mood_label IS NULL` AND `preview_url IS NOT NULL`.
- Already-classified tracks are skipped.
- Respects iTunes rate limit of ~20 calls/minute — space requests accordingly.

### 4.6 NULL Handling

- Tracks without an available iTunes audio preview: `mood_label = NULL`, `mood_confidence = NULL`.
- dbt tests assert the NULL rate of `mood_label` stays within an acceptable threshold (exact threshold TBD during Phase 3).
- All downstream models and API endpoints handle NULLs gracefully — mood-based aggregations exclude NULL rows.

### 4.7 Performance Documentation

- Document inference time per track in the README.
- Document target sample rate (`TARGET_SAMPLE_RATE`) in the README.
- If inference exceeds a few seconds per track, consider async processing or less frequent scheduling.

---

## 5. dbt Transformation

### 5.1 Layer Architecture

```
raw schema (PostgreSQL)
  │
  ▼
staging (stg_)          — 1:1 with raw tables, clean types, rename columns
  │
  ▼
intermediate (int_)     — joins, deduplication, business logic
  │
  ▼
marts (mart_ / dim_ / fact_)  — star schema, pre-aggregated tables
```

### 5.2 Staging Models

| Model | Source | Purpose |
| --- | --- | --- |
| `stg_recent_tracks` | `raw.recent_tracks` | Cast types, rename columns, extract `hour` from `played_at`, generate surrogate keys |
| `stg_track_tags` | `raw.track_tags` | Parse tags array, normalize tag names (lowercase, trim) |
| `stg_artists` | `raw.artists` | Cast types, extract listener/play counts |
| `stg_artist_tags` | `raw.artist_tags` | Parse tags array — used as genre proxy for `dim_artists.genres` |
| `stg_weather` | `raw.weather` | Cast types, standardize column names |

### 5.3 Intermediate Models

| Model | Purpose |
| --- | --- |
| `int_listens_enriched` | Join `stg_recent_tracks` with track/artist references, attach surrogate keys |
| `int_artists_snapshot` | Prepare artist data for SCD Type 2 processing (compare current vs. previous `listener_count`, `play_count`) |

### 5.4 Mart Models

| Model | Type | Description |
| --- | --- | --- |
| `fact_listens` | Fact | One row per listen event. Columns: `listen_id`, `track_id`, `artist_id`, `date_id`, `played_at`, `hour`, `ms_played` |
| `dim_tracks` | Dimension | One row per track. Includes `top_tags`, `preview_url`, `mood_label`, `mood_confidence`. |
| `dim_artists` | Dimension (SCD2) | One row per artist per version. `genres` from Last.fm top tags. Includes `listener_count`, `play_count`, `valid_from`, `valid_to`, `is_current`. |
| `dim_dates` | Dimension | One row per calendar date. Pre-populated or generated via dbt `date_spine`. Columns: `date_id`, `day_of_week`, `month`, `year`, `is_weekend`. |
| `dim_weather` | Dimension | One row per date per city. Joined to `dim_dates` on `date_id`. |
| `mart_listening_summary` | Mart (pre-aggregated) | One row per calendar date. See Section 5.5. |

### 5.5 `mart_listening_summary` Specification

One row per calendar date. This table is the primary query target for FastAPI endpoints.

| Column | Type | Description |
| --- | --- | --- |
| `date_id` | DATE | Calendar date (PK) |
| `total_listens` | INTEGER | Count of listens on this date |
| `unique_tracks` | INTEGER | Count of distinct tracks on this date |
| `unique_artists` | INTEGER | Count of distinct artists on this date |
| `total_ms_played` | BIGINT | Sum of `ms_played` on this date |
| `mood_happy_count` | INTEGER | Count of listens with `mood_label = 'happy'` on this date |
| `mood_sad_count` | INTEGER | Count of listens with `mood_label = 'sad'` on this date |
| `mood_angry_count` | INTEGER | Count of listens with `mood_label = 'angry'` on this date |
| `mood_calm_count` | INTEGER | Count of listens with `mood_label = 'calm'` on this date |
| `mood_energetic_count` | INTEGER | Count of listens with `mood_label = 'energetic'` on this date |
| `mood_melancholic_count` | INTEGER | Count of listens with `mood_label = 'melancholic'` on this date |
| `mood_null_count` | INTEGER | Count of listens with `mood_label IS NULL` on this date |

**Note:** The exact list of mood columns depends on the final mood classes from the model. Add one `mood_<label>_count` column per class. The column names above are illustrative — finalize after confirming model output classes in Phase 3.

### 5.6 SCD Type 2 — `dim_artists`

- On each dbt run, compare incoming artist data (`listener_count`, `play_count`) against the current record (`is_current = TRUE`).
- If `listener_count` or `play_count` has changed:
  1. Set `valid_to = current_date` and `is_current = FALSE` on the existing record.
  2. Insert a new record with updated values, `valid_from = current_date`, `valid_to = NULL`, `is_current = TRUE`.
- Implementation via dbt snapshot (`dbt snapshot`) or custom incremental logic.

### 5.7 dbt Tests

| Test Type | Applied To |
| --- | --- |
| `not_null` | All primary keys, all foreign keys, `played_at`, `track_name`, `artist_name` |
| `unique` | `fact_listens.listen_id`, `dim_tracks.track_id`, `dim_dates.date_id`, `mart_listening_summary.date_id` |
| `accepted_values` | `dim_dates.day_of_week` (Mon–Sun), `dim_dates.is_weekend` (true/false), `dim_tracks.mood_label` (exact model class list + NULL) |
| `relationships` | `fact_listens.track_id` → `dim_tracks.track_id`, `fact_listens.artist_id` → `dim_artists.artist_id`, `fact_listens.date_id` → `dim_dates.date_id` |
| Custom: range check | `dim_tracks.mood_confidence` between 0 and 1 when not NULL |
| Custom: NULL rate | `dim_tracks.mood_label` NULL rate below acceptable threshold (TBD) |

### 5.8 Handling NULL `mood_label`

- All downstream models treat `mood_label IS NULL` gracefully.
- Mood distribution calculations exclude NULLs from percentage calculations but track `mood_null_count` separately.
- API endpoints return the NULL count alongside mood distributions so the frontend can display "X% of tracks unclassified."

### 5.9 Warehouse Portability

- All dbt models must avoid PostgreSQL-specific SQL (e.g., `::` casting, `ILIKE`, array operators) to facilitate the Phase 7 Snowflake migration.
- Use dbt's built-in macros for type casting (`cast()`), date functions (`dbt.date_trunc()`), and cross-database compatibility where available.
- If Postgres-specific SQL is unavoidable, isolate it behind a dbt macro that can be swapped for a Snowflake equivalent.

---

## 6. Data Quality — Great Expectations

### 6.1 Expectation Suites

#### Suite: `raw_recent_tracks`

| Expectation | Details |
| --- | --- |
| `expect_column_values_to_not_be_null` | `track_name`, `artist_name`, `played_at` |
| `expect_column_values_to_be_dateutil_parseable` | `played_at` |
| `expect_column_values_to_be_less_than` | `played_at` < current timestamp (not in the future) |
| `expect_table_row_count_to_be_between` | min=1 (flag if 0 rows after a non-empty ingestion window) |

#### Suite: `dim_tracks_mood`

| Expectation | Details |
| --- | --- |
| `expect_column_values_to_be_between` | `mood_confidence` between 0 and 1 (where not NULL) |
| `expect_column_values_to_be_in_set` | `mood_label` in set of valid model classes (where not NULL) |
| `expect_column_proportion_of_unique_values_to_be_between` | `mood_label` NULL rate below threshold (TBD) |

#### Suite: `raw_weather`

| Expectation | Details |
| --- | --- |
| `expect_column_values_to_not_be_null` | `date`, `temp_c`, `weather_code` |
| `expect_column_values_to_be_between` | `temp_c` between -60 and 60 (sanity check) |

### 6.2 Gating Logic

- GE validation runs **after** ingestion and mood classification and **before** dbt transformation.
- If any expectation suite fails:
  1. The dbt transform step is **skipped** for that run.
  2. A Slack alert is sent with the suite name, failed expectations, and row counts.
  3. The Airflow task is marked as failed.
- Failed data remains in raw tables for inspection. It is not deleted.

---

## 7. Airflow Orchestration

### 7.1 DAG Definitions

#### `lastfm_ingest_dag`

| Property | Value |
| --- | --- |
| Schedule | `*/30 * * * *` (every 30 minutes) |
| Tasks | `fetch_recent_tracks` → `fetch_track_tags` (for new tracks) → `fetch_artist_info` (for new artists) → `fetch_artist_tags` (for new artists) |
| Dependencies | None (runs independently) |
| Failure handling | Slack alert on task failure, task retries 2× with 60s delay |

#### `weather_ingest_dag`

| Property | Value |
| --- | --- |
| Schedule | `0 2 * * *` (nightly at 2 AM) |
| Tasks | `fetch_daily_weather` |
| Dependencies | None (runs independently) |
| Failure handling | Slack alert on task failure, task retries 2× with 60s delay |

#### `mood_classification_dag`

| Property | Value |
| --- | --- |
| Schedule | Triggered via sensor after `lastfm_ingest_dag` succeeds |
| Tasks | `find_unclassified_tracks` → `fetch_itunes_previews` → `run_librosa_inference` → `write_mood_labels` |
| Dependencies | Waits for `lastfm_ingest_dag` success via `ExternalTaskSensor` |
| Rate limiting | iTunes calls throttled to ~20/minute |
| Failure handling | Slack alert on task failure. Individual track failures are logged but do not abort the DAG — remaining tracks continue processing. |

#### `data_quality_dag`

| Property | Value |
| --- | --- |
| Schedule | Triggered via sensor after `mood_classification_dag` succeeds |
| Tasks | `run_ge_recent_tracks` → `run_ge_mood` → `run_ge_weather` |
| Dependencies | Waits for `mood_classification_dag` success via `ExternalTaskSensor` |
| Failure handling | Slack alert on any GE failure, downstream `dbt_transform_dag` is not triggered |

#### `dbt_transform_dag`

| Property | Value |
| --- | --- |
| Schedule | Triggered via sensor after `data_quality_dag` succeeds |
| Tasks | `dbt_run` → `dbt_test` → `dbt_docs_generate` |
| Dependencies | Waits for `data_quality_dag` success via `ExternalTaskSensor` |
| Failure handling | Slack alert on dbt run/test failure |

### 7.2 DAG Dependency Chain

```
lastfm_ingest_dag (every 30 min)
        │
        ▼
mood_classification_dag (sensor-triggered)
        │
        ▼
data_quality_dag (sensor-triggered)
        │
        ▼ (only if GE passes)
dbt_transform_dag (sensor-triggered)

weather_ingest_dag (nightly, independent)
        │
        ▼ (feeds into next dbt_transform_dag run via raw.weather)
```

### 7.3 Backfill Support

- All DAGs support `catchup=True` for backfill.
- `dbt_transform_dag` can be manually triggered for a specific date range via Airflow CLI: `airflow dags trigger dbt_transform_dag --conf '{"start_date": "2026-02-01", "end_date": "2026-02-28"}'`.
- dbt models use `{{ var('start_date', none) }}` and `{{ var('end_date', none) }}` to optionally scope transformations to a date range.

### 7.4 Secret Management in Airflow

- All secrets stored as Airflow Variables or Connections, populated from `.env` at container startup.
- Variables: `LASTFM_API_KEY`, `LASTFM_USERNAME`, `SLACK_WEBHOOK_URL`, `OPENMETEO_CITY`.
- Connections: `postgres_default` (or `snowflake_default` after Phase 7) with host/port/db/user/password.

### 7.5 Breaking Schema Change Simulation

- During Phase 4, a breaking schema change will be intentionally introduced (e.g., renaming a column in a raw table, adding a required field).
- The handling process must be documented in the README:
  1. What changed.
  2. How dbt models were updated.
  3. Whether a backfill was needed.
  4. How downstream consumers (FastAPI) were affected and resolved.

---

## 8. Snowflake Migration (Phase 7)

### 8.1 Prerequisites

- Snowflake free trial account ($400 credits, no credit card).
- Snowflake warehouse, database, and schema created.
- `dbt-snowflake` adapter installed.

### 8.2 Migration Steps

1. **dbt profile update:** Add a `snowflake` target in `profiles.yml` with account, user, password, warehouse, database, schema.
2. **Run dbt against Snowflake:** `dbt run --target snowflake`. Fix any SQL incompatibilities.
3. **Seed data:** Run initial full load of raw data into Snowflake (one-time migration script or `dbt seed`).
4. **Validate dbt tests:** `dbt test --target snowflake` — all tests must pass.
5. **Update Airflow connection:** Swap `postgres_default` for `snowflake_default`.
6. **Validate FastAPI:** Hit all endpoints and verify responses match PostgreSQL baseline.
7. **Document:** All SQL changes, incompatibilities found, and migration steps recorded in README.

### 8.3 Expected Incompatibilities

| Postgres Feature | Snowflake Equivalent | Mitigation |
| --- | --- | --- |
| `::` type casting | `CAST()` / `TRY_CAST()` | Use `CAST()` from the start |
| `SERIAL` / auto-increment PK | `AUTOINCREMENT` or `IDENTITY` | Use dbt surrogate key macro |
| `JSONB` operators | `PARSE_JSON()` / `GET_PATH()` | Isolate behind dbt macros |
| `ILIKE` | `ILIKE` (supported in Snowflake) | No change needed |
| `NOW()` | `CURRENT_TIMESTAMP()` | Use `CURRENT_TIMESTAMP()` from the start |

---

## 9. Environment Variables

All variables required by the pipeline, documented in `.env.example`:

```
# Last.fm API
LASTFM_API_KEY=
LASTFM_USERNAME=

# Database (PostgreSQL — Phases 1–6)
DB_CONNECTION_STRING=postgresql://localhost:5432/music_intelligence

# Database (Snowflake — Phase 7)
SNOWFLAKE_ACCOUNT=
SNOWFLAKE_USER=
SNOWFLAKE_PASSWORD=
SNOWFLAKE_WAREHOUSE=
SNOWFLAKE_DATABASE=
SNOWFLAKE_SCHEMA=

# Weather
OPENMETEO_CITY=

# Slack
SLACK_WEBHOOK_URL=
```

---

## 10. Acceptance Criteria

| Criteria | Verification |
| --- | --- |
| Last.fm ingestion runs every 30 min and loads new scrobbles incrementally | Inspect `raw.recent_tracks` row counts over 3+ days |
| Pagination works — all scrobbles fetched, not just first page | Compare row count against Last.fm profile's total scrobble count |
| Deduplication works — no duplicate `(played_at, track_name, artist_name)` tuples | SQL verification query |
| Dead letter queue captures malformed records | Intentionally send malformed data and verify it appears in `raw.raw_failed` |
| Last.fm rate limit (5 req/sec) is respected | Monitor request timing in logs |
| iTunes preview matching works with confidence check | Verify known tracks return correct preview URLs; verify mismatches return NULL |
| Mood classification produces valid labels | Inspect `dim_tracks.mood_label` values against model class list |
| `mood_confidence` is between 0 and 1 | SQL range check |
| Tracks without iTunes preview have `mood_label = NULL` | Filter for `preview_url IS NULL` and verify `mood_label IS NULL` |
| Slack alerts fire on ingestion failure | Trigger a failure and verify Slack message |
| dbt models produce correct star schema | `dbt test` passes with 0 failures |
| SCD Type 2 tracks artist changes | Manually change an artist's `listener_count` and verify two rows with correct `valid_from`/`valid_to` |
| GE blocks dbt on bad data | Insert a `played_at` in the future, run GE, verify dbt does not run |
| Airflow DAGs chain correctly (5 DAGs) | Verify `dbt_transform_dag` only runs after `data_quality_dag` succeeds |
| Mood classification DAG sits between ingest and quality check | Verify chain: ingest → mood → GE → dbt |
| Backfill works | Trigger a backfill for a past date range and verify mart tables update |
| Snowflake migration passes | `dbt test --target snowflake` passes, FastAPI returns same data |
