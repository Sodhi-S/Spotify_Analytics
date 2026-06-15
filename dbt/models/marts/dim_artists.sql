with artist_versions as (
    select * from {{ ref('artists_snapshot') }}
),

artist_images as (
    select
        artist_id,
        image_url,
        image_source,
        image_width,
        image_height,
        image_updated_at
    from {{ source('raw', 'artist_image_enrichments') }}
    where image_url is not null
)

select
    {{ surrogate_key(["artist_versions.artist_id", "artist_versions.dbt_valid_from"]) }} as artist_version_id,
    artist_versions.artist_id,
    artist_versions.artist_name as name,
    artist_versions.artist_mbid,
    artist_versions.genres,
    artist_versions.listener_count,
    artist_versions.play_count,
    artist_versions.bio,
    artist_images.image_url,
    artist_images.image_source,
    artist_images.image_width,
    artist_images.image_height,
    artist_images.image_updated_at,
    cast(artist_versions.dbt_valid_from as date) as valid_from,
    cast(artist_versions.dbt_valid_to as date) as valid_to,
    case when artist_versions.dbt_valid_to is null then true else false end as is_current
from artist_versions
left join artist_images on artist_versions.artist_id = artist_images.artist_id
