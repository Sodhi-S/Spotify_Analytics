select
    weather.date_id,
    weather.city,
    weather.temp_c,
    weather.precipitation,
    weather.weather_code
from {{ ref('stg_weather') }} weather
