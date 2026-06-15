{{ config(materialized='incremental', unique_key='track_id', on_schema_change='sync_all_columns') }}

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
),

emotion_features as (
    select
        track_id,
        valence,
        energy,
        mood_label,
        predicted_moods,
        model_name,
        model_version,
        classified_at
    from {{ source('raw', 'track_emotion_features') }}
    where error_message is null
),

track_images as (
    select
        track_id,
        album_image_url,
        album_image_source,
        album_image_width,
        album_image_height,
        album_image_updated_at
    from {{ source('raw', 'track_image_enrichments') }}
    where album_image_url is not null
)

select
    tracks.track_id,
    tracks.name,
    tracks.artist_id,
    tracks.artist_name,
    tracks.album,
    tracks.top_tags,
    existing.preview_url,
    track_images.album_image_url,
    track_images.album_image_source,
    track_images.album_image_width,
    track_images.album_image_height,
    track_images.album_image_updated_at,
    coalesce(emotion_features.mood_label, existing.mood_label) as mood_label,
    existing.mood_confidence,
    emotion_features.valence,
    emotion_features.energy,
    emotion_features.predicted_moods,
    emotion_features.model_name as emotion_model_name,
    emotion_features.model_version as emotion_model_version,
    emotion_features.classified_at as emotion_classified_at
from tracks
left join existing on tracks.track_id = existing.track_id
left join emotion_features on tracks.track_id = emotion_features.track_id
left join track_images on tracks.track_id = track_images.track_id
