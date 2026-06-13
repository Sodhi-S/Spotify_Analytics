with weather as (
    select * from {{ ref('stg_weather') }}
)

select
    date_id,
    city,
    temp_max_c,
    temp_mean_c,
    temp_min_c,
    precipitation,
    rain,
    snowfall,
    precipitation_hours,
    weather_code,
    case
        when weather_code in (0, 1) then 'Clear'
        when weather_code in (2, 3) then 'Cloudy'
        when weather_code in (45, 48) then 'Fog'
        when weather_code in (51, 53, 55) then 'Drizzle'
        when weather_code in (61, 63, 65) then 'Rain'
        when weather_code in (66, 67) then 'Freezing Rain'
        when weather_code in (71, 73, 75, 77) then 'Snow'
        when weather_code in (80, 81, 82) then 'Showers'
        when weather_code in (85, 86) then 'Snow Showers'
        when weather_code in (95, 96, 99) then 'Thunderstorm'
        else 'Unknown'
    end as weather_category,
    case
        when temp_mean_c is null then 'Unknown'
        when temp_mean_c < 0 then 'Freezing'
        when temp_mean_c < 10 then 'Cold'
        when temp_mean_c < 20 then 'Mild'
        when temp_mean_c < 28 then 'Warm'
        else 'Hot'
    end as temperature_bucket,
    case
        when extract(month from date_id) in (12, 1, 2) then 'Winter'
        when extract(month from date_id) in (3, 4, 5) then 'Spring'
        when extract(month from date_id) in (6, 7, 8) then 'Summer'
        else 'Fall'
    end as season,
    case when coalesce(precipitation, 0) > 0 then true else false end as had_precipitation,
    case when coalesce(rain, precipitation, 0) > 0 then true else false end as had_rain,
    case when coalesce(snowfall, 0) > 0 then true else false end as had_snow,
    source,
    fetched_at
from weather
