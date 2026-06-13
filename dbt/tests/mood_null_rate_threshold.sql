with counts as (
    select
        count(*) as total_tracks,
        sum(case when mood_label is null then 1 else 0 end) as null_tracks
    from {{ ref('dim_tracks') }}
)

select *
from counts
where total_tracks > 0
  and cast(null_tracks as numeric) / total_tracks > {{ var('mood_null_rate_threshold', 1.0) }}
