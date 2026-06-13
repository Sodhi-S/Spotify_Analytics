{{ config(materialized='incremental', unique_key='track_id') }}

with tracks as (
    select
        listens.track_id,
        min(listens.track_name) as name,
        min(listens.artist_id) as artist_id,
        min(listens.artist_name) as artist_name,
        min(listens.album) as album,
        coalesce({{ tag_list_agg("track_tags.tag_name") }}, '') as top_tags
    from {{ ref('stg_recent_tracks') }} listens
    left join {{ ref('stg_track_tags') }} track_tags
        on listens.track_id = track_tags.track_id
    group by listens.track_id
),

existing as (
    {% if is_incremental() %}
        select
            track_id,
            preview_url,
            mood_label,
            mood_confidence
        from {{ this }}
    {% else %}
        select
            cast(null as {{ dbt.type_string() }}) as track_id,
            cast(null as {{ dbt.type_string() }}) as preview_url,
            cast(null as {{ dbt.type_string() }}) as mood_label,
            cast(null as numeric) as mood_confidence
        where 1 = 0
    {% endif %}
)

select
    tracks.track_id,
    tracks.name,
    tracks.artist_id,
    tracks.artist_name,
    tracks.album,
    tracks.top_tags,
    existing.preview_url,
    existing.mood_label,
    existing.mood_confidence
from tracks
left join existing on tracks.track_id = existing.track_id
