with dates as (
    select distinct date_id
    from {{ ref('int_listens_enriched') }}
)

select
    date_id,
    {{ day_of_week_name("date_id") }} as day_of_week,
    cast(extract(month from date_id) as integer) as month,
    cast(extract(year from date_id) as integer) as year,
    {{ is_weekend("date_id") }} as is_weekend
from dates
