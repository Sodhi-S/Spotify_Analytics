# Local App Runbook

This runbook covers the normal local workflow:

1. Start Postgres
2. Ingest Last.fm/weather data
3. Run dbt
4. Start the backend
5. Start the frontend

Run commands from the project root unless noted otherwise.

## 1. Start The Database

Start Docker Desktop first, then run:

```bash
docker compose up -d postgres
```

Check that Postgres is healthy:

```bash
docker compose ps
```

Initialize raw tables if you have not already:

```bash
bash scripts/db_init.sh
```

Check schemas/tables:

```bash
bash scripts/db_status.sh
```

## 2. Configure Environment

Create `.env` if needed:

```bash
cp .env.example .env
```

Fill these values:

```text
LASTFM_API_KEY=your_lastfm_api_key
LASTFM_USERNAME=your_lastfm_username
OPENMETEO_CITY=Toronto
DB_CONNECTION_STRING=postgresql+psycopg://postgres:postgres@localhost:5432/music_intelligence
```

## 3. Install Python Dependencies

Use your conda env:

```bash
conda activate ve
python -m pip install -r backend/requirements.txt
python -m pip install -r requirements-dbt.txt
```

## 4. Ingest Last.fm And Weather Data

Run ingestion once:

```bash
PYTHONPATH=backend:scripts python scripts/run_ingest_once.py
```

Check raw row counts:

```bash
bash scripts/db_status.sh
```

Useful TablePlus queries:

```sql
select count(*) from raw.recent_tracks;
select * from raw.recent_tracks order by played_at desc limit 20;
select * from raw.raw_failed order by failed_at desc limit 20;
```

To simulate cron behavior without real cron:

```bash
PYTHONPATH=backend:scripts python scripts/run_ingest_scheduler.py --interval-seconds 60 --runs 2
```

For the real 30-minute interval:

```bash
PYTHONPATH=backend:scripts python scripts/run_ingest_scheduler.py --interval-seconds 1800
```

## 5. Run dbt

Run dbt from the `dbt` directory:

```bash
cd dbt
/opt/anaconda3/envs/ve/bin/dbt debug --profiles-dir .
/opt/anaconda3/envs/ve/bin/dbt run --profiles-dir . --select staging intermediate
/opt/anaconda3/envs/ve/bin/dbt snapshot --profiles-dir .
/opt/anaconda3/envs/ve/bin/dbt run --profiles-dir . --select marts
/opt/anaconda3/envs/ve/bin/dbt test --profiles-dir .
cd ..
```

This creates/updates:

```text
public.stg_recent_tracks
public.int_listens_enriched
public.fact_listens
public.dim_tracks
public.dim_artists
public.dim_dates
public.dim_weather
public.mart_listening_summary
public.mart_tag_listen_counts
```

Quick verification:

```bash
docker compose exec -T postgres psql -U postgres -d music_intelligence -c "select count(*) from public.fact_listens;"
docker compose exec -T postgres psql -U postgres -d music_intelligence -c "select count(*) from public.mart_listening_summary;"
```

## 6. Run The Backend

From the project root:

```bash
conda activate ve
PYTHONPATH=backend uvicorn app.main:app --reload --port 8000
```

Verify:

```bash
curl http://localhost:8000/health
curl "http://localhost:8000/api/stats/overview?period=30d"
```

If `/api/stats/overview` errors with `public.mart_listening_summary does not exist`, run dbt first.

## 7. Run The Frontend

In a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the URL Vite prints, usually:

```text
http://localhost:3000
```

If port 3000 is busy, Vite may use another port like `3001`.

## Normal Daily Loop

After setup, the usual loop is:

```bash
PYTHONPATH=backend:scripts python scripts/run_ingest_once.py

cd dbt
/opt/anaconda3/envs/ve/bin/dbt run --profiles-dir . --select staging intermediate
/opt/anaconda3/envs/ve/bin/dbt snapshot --profiles-dir .
/opt/anaconda3/envs/ve/bin/dbt run --profiles-dir . --select marts
/opt/anaconda3/envs/ve/bin/dbt test --profiles-dir .
cd ..

PYTHONPATH=backend uvicorn app.main:app --reload --port 8000
```

Then run the frontend:

```bash
cd frontend
npm run dev
```

