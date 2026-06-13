with source as (
    select * from {{ source('raw', 'recent_tracks') }}
),

cleaned as (
    select
        {{ surrogate_key(["track_name", "artist_name", "played_at"]) }} as listen_id,
        {{ surrogate_key(["track_name", "artist_name"]) }} as track_id,
        {{ surrogate_key(["artist_name"]) }} as artist_id,
        cast(track_name as {{ dbt.type_string() }}) as track_name,
        cast(artist_name as {{ dbt.type_string() }}) as artist_name,
        cast(album as {{ dbt.type_string() }}) as album,
        played_at,
        cast(played_at as date) as date_id,
        {{ hour_from_timestamp("played_at") }} as hour,
        cast(track_mbid as {{ dbt.type_string() }}) as track_mbid,
        cast(artist_mbid as {{ dbt.type_string() }}) as artist_mbid,
        fetched_at
    from source
    where track_name is not null
      and artist_name is not null
      and played_at is not null
      {% if var('start_date', none) is not none %}
        and cast(played_at as date) >= cast('{{ var("start_date") }}' as date)
      {% endif %}
      {% if var('end_date', none) is not none %}
        and cast(played_at as date) <= cast('{{ var("end_date") }}' as date)
      {% endif %}
)

select * from cleaned
