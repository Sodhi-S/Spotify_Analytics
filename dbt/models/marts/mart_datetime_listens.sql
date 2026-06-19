-- One row per listen, denormalized for the DateTime page.
-- Timestamps are localized to LISTENING_TIMEZONE (default America/Toronto) so
-- hour-of-day, day-of-week, and month buckets reflect the listener's wall clock
-- instead of UTC. Period filtering happens in the service layer on local_date.

with listens as (
    select
        listen_id,
        track_id,
        artist_id,
        played_at,
        {{ to_local_timestamp('played_at') }} as local_played_at
    from {{ ref('int_listens_enriched') }}
)

select
    l.listen_id,
    l.track_id,
    l.artist_id,
    l.played_at,
    cast(l.local_played_at as date) as local_date,
    cast(extract(year from l.local_played_at) as integer) as local_year,
    cast(extract(month from l.local_played_at) as integer) as local_month,
    {{ year_month_label('l.local_played_at') }} as year_month,
    {{ hour_from_timestamp('l.local_played_at') }} as local_hour,
    {{ day_of_week_name('l.local_played_at') }} as day_of_week,
    cast({{ day_of_week_number('l.local_played_at') }} as integer) as dow_num,
    {{ is_weekend('l.local_played_at') }} as is_weekend,
    dt.name as track_name,
    dt.artist_name,
    dt.album_image_url,
    dt.top_tags,
    dt.mood_label,
    dt.valence,
    dt.energy
from listens l
left join {{ ref('dim_tracks') }} dt on l.track_id = dt.track_id
