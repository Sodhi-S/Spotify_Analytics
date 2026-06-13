select
    weather.date_id,
    weather.city,
    weather.temp_max_c as temp_c,
    weather.temp_mean_c,
    weather.temp_min_c,
    weather.precipitation,
    weather.rain,
    weather.snowfall,
    weather.precipitation_hours,
    weather.weather_code,
    weather.weather_category,
    weather.temperature_bucket,
    weather.season,
    weather.had_precipitation,
    weather.had_rain,
    weather.had_snow,
    weather.source
from {{ ref('int_weather_enriched') }} weather
