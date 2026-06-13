with source as (
    select * from {{ source('raw', 'track_tags') }}
),

flattened as (
    select
        {{ surrogate_key(["track_name", "artist_name"]) }} as track_id,
        cast(track_name as {{ dbt.type_string() }}) as track_name,
        cast(artist_name as {{ dbt.type_string() }}) as artist_name,
        {{ json_tag_name("tag_item") }} as tag_name,
        {{ json_tag_count("tag_item") }} as tag_count,
        fetched_at
    from source tt
    {{ json_array_lateral("tt.tags", "tag_item") }}
)

select *
from flattened
where tag_name is not null
