select
    listen_id,
    track_id,
    artist_id,
    date_id,
    played_at,
    hour,
    ms_played
from {{ ref('int_listens_enriched') }}
