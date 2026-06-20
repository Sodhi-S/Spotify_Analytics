with listens as (
    select * from {{ ref('fact_listens') }}
),

tracks as (
    select * from {{ ref('dim_tracks') }}
)

select
    listens.user_id,
    listens.date_id,
    count(*) as total_listens,
    count(distinct listens.track_id) as unique_tracks,
    count(distinct listens.artist_id) as unique_artists,
    coalesce(sum(listens.ms_played), 0) as total_ms_played,
    sum(case when tracks.mood_label = 'happy' then 1 else 0 end) as mood_happy_count,
    sum(case when tracks.mood_label = 'sad' then 1 else 0 end) as mood_sad_count,
    sum(case when tracks.mood_label = 'angry' then 1 else 0 end) as mood_angry_count,
    sum(case when tracks.mood_label = 'calm' then 1 else 0 end) as mood_calm_count,
    sum(case when tracks.mood_label = 'energetic' then 1 else 0 end) as mood_energetic_count,
    sum(case when tracks.mood_label = 'melancholic' then 1 else 0 end) as mood_melancholic_count,
    sum(case when tracks.mood_label is null then 1 else 0 end) as mood_null_count
from listens
left join tracks on listens.track_id = tracks.track_id
group by
    listens.user_id,
    listens.date_id
