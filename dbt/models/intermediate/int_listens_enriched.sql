select
    user_id,
    listen_id,
    track_id,
    artist_id,
    track_name,
    artist_name,
    album,
    date_id,
    played_at,
    hour,
    cast(null as integer) as ms_played
from {{ ref('stg_recent_tracks') }}
