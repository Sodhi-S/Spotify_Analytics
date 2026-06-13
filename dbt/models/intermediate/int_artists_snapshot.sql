with listen_artists as (
    select distinct
        artist_id,
        artist_name
    from {{ ref('stg_recent_tracks') }}
),

artists as (
    select * from {{ ref('stg_artists') }}
),

artist_tags as (
    select * from {{ ref('stg_artist_tags') }}
)

select
    listen_artists.artist_id,
    listen_artists.artist_name,
    artists.artist_mbid,
    coalesce({{ tag_list_agg("artist_tags.tag_name") }}, '') as genres,
    max(artists.listener_count) as listener_count,
    max(artists.play_count) as play_count,
    max(artists.bio) as bio,
    max(artists.fetched_at) as fetched_at
from listen_artists
left join artists on listen_artists.artist_id = artists.artist_id
left join artist_tags on listen_artists.artist_id = artist_tags.artist_id
group by
    listen_artists.artist_id,
    listen_artists.artist_name,
    artists.artist_mbid
