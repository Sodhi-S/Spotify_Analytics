#!/usr/bin/env bash
set -euo pipefail

docker compose ps
docker compose exec -T postgres psql -U postgres -d music_intelligence -c "\dn"
docker compose exec -T postgres psql -U postgres -d music_intelligence -c "\dt raw.*"
docker compose exec -T postgres psql -U postgres -d music_intelligence -c "select 'recent_tracks' as table_name, count(*) from raw.recent_tracks union all select 'raw_failed', count(*) from raw.raw_failed union all select 'weather', count(*) from raw.weather;"
