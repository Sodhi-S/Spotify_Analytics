select *
from {{ ref('dim_tracks') }}
where mood_confidence is not null
  and (mood_confidence < 0 or mood_confidence > 1)
