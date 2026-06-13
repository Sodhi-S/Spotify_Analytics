with source as (
    select * from {{ source('raw', 'artist_tags') }}
),

flattened as (
    select
        {{ surrogate_key(["artist_name"]) }} as artist_id,
        cast(artist_name as {{ dbt.type_string() }}) as artist_name,
        {{ json_tag_name("tag_item") }} as tag_name,
        {{ json_tag_count("tag_item") }} as tag_count,
        fetched_at
    from source at
    {{ json_array_lateral("at.tags", "tag_item") }}
)

select *
from flattened
where tag_name is not null
