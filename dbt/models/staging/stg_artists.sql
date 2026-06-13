with source as (
    select * from {{ source('raw', 'artists') }}
)

select
    {{ surrogate_key(["artist_name"]) }} as artist_id,
    cast(artist_name as {{ dbt.type_string() }}) as artist_name,
    cast(artist_mbid as {{ dbt.type_string() }}) as artist_mbid,
    cast(listener_count as bigint) as listener_count,
    cast(play_count as bigint) as play_count,
    cast(bio as {{ dbt.type_string() }}) as bio,
    fetched_at
from source
where artist_name is not null
