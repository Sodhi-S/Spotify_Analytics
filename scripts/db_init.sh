#!/usr/bin/env bash
set -euo pipefail

docker compose up -d postgres

echo "Waiting for Postgres..."
until docker compose exec -T postgres pg_isready -U postgres -d music_intelligence >/dev/null 2>&1; do
  sleep 1
done

for sql_file in backend/sql/*.sql; do
  echo "Applying ${sql_file}..."
  docker compose exec -T postgres psql -U postgres -d music_intelligence < "${sql_file}"
done

echo "Initialized raw schema."
docker compose exec -T postgres psql -U postgres -d music_intelligence -c "\dn"
docker compose exec -T postgres psql -U postgres -d music_intelligence -c "\dt raw.*"
