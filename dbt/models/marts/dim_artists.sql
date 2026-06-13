select
    {{ surrogate_key(["artist_id", "dbt_valid_from"]) }} as artist_version_id,
    artist_id,
    artist_name as name,
    artist_mbid,
    genres,
    listener_count,
    play_count,
    bio,
    cast(dbt_valid_from as date) as valid_from,
    cast(dbt_valid_to as date) as valid_to,
    case when dbt_valid_to is null then true else false end as is_current
from {{ ref('artists_snapshot') }}
