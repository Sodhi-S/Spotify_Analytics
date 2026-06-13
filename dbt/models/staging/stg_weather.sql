with source as (
    select * from {{ source('raw', 'weather') }}
)

select
    cast(date as date) as date_id,
    cast(city as {{ dbt.type_string() }}) as city,
    cast(temp_c as numeric) as temp_max_c,
    cast(coalesce(temp_mean_c, temp_c) as numeric) as temp_mean_c,
    cast(temp_min_c as numeric) as temp_min_c,
    cast(precipitation as numeric) as precipitation,
    cast(rain as numeric) as rain,
    cast(snowfall as numeric) as snowfall,
    cast(precipitation_hours as numeric) as precipitation_hours,
    cast(weather_code as integer) as weather_code,
    cast(source as {{ dbt.type_string() }}) as source,
    fetched_at
from source
where date is not null
  and city is not null
  {% if var('start_date', none) is not none %}
    and cast(date as date) >= cast('{{ var("start_date") }}' as date)
  {% endif %}
  {% if var('end_date', none) is not none %}
    and cast(date as date) <= cast('{{ var("end_date") }}' as date)
  {% endif %}
