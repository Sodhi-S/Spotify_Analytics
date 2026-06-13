alter table raw.weather
    add column if not exists temp_mean_c numeric,
    add column if not exists temp_min_c numeric,
    add column if not exists rain numeric,
    add column if not exists snowfall numeric,
    add column if not exists precipitation_hours numeric,
    add column if not exists source text not null default 'open_meteo';

update raw.weather
set temp_mean_c = coalesce(temp_mean_c, temp_c)
where temp_mean_c is null;
