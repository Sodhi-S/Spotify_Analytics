select
    user_id,
    date_id,
    count(*) as row_count
from {{ ref('mart_listening_summary') }}
group by user_id, date_id
having count(*) > 1
