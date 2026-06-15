create schema if not exists raw;

create table if not exists raw.ingestion_metadata (
    source text primary key,
    last_fetched_at timestamptz not null,
    updated_at timestamptz not null default current_timestamp
);

create table if not exists raw.raw_failed (
    id bigserial primary key,
    source text not null,
    raw_payload jsonb not null,
    error_message text not null,
    failed_at timestamptz not null default current_timestamp
);

create table if not exists raw.recent_tracks (
    id bigserial primary key,
    track_name text not null,
    artist_name text not null,
    album text,
    played_at timestamptz not null,
    track_mbid text,
    artist_mbid text,
    raw_payload jsonb not null,
    fetched_at timestamptz not null default current_timestamp,
    constraint uq_recent_tracks_dedupe unique (played_at, track_name, artist_name)
);

create index if not exists idx_recent_tracks_played_at
    on raw.recent_tracks (played_at);

create index if not exists idx_recent_tracks_artist_track
    on raw.recent_tracks (artist_name, track_name);

create table if not exists raw.track_tags (
    id bigserial primary key,
    track_name text not null,
    artist_name text not null,
    tags jsonb not null,
    fetched_at timestamptz not null default current_timestamp,
    constraint uq_track_tags_track_artist unique (track_name, artist_name)
);

create table if not exists raw.artists (
    id bigserial primary key,
    artist_name text not null,
    artist_mbid text,
    listener_count bigint,
    play_count bigint,
    similar_artists jsonb not null default '[]'::jsonb,
    bio text,
    raw_payload jsonb not null,
    fetched_at timestamptz not null default current_timestamp,
    constraint uq_artists_artist_name unique (artist_name)
);

create table if not exists raw.artist_tags (
    id bigserial primary key,
    artist_name text not null,
    tags jsonb not null,
    fetched_at timestamptz not null default current_timestamp,
    constraint uq_artist_tags_artist_name unique (artist_name)
);

create table if not exists raw.track_image_enrichments (
    track_id text primary key,
    album_image_url text,
    album_image_source text,
    album_image_width integer,
    album_image_height integer,
    album_image_updated_at timestamptz,
    raw_payload jsonb not null default '{}'::jsonb,
    unresolved_reason text,
    attempted_at timestamptz not null default current_timestamp
);

create table if not exists raw.artist_image_enrichments (
    artist_id text primary key,
    image_url text,
    image_source text,
    image_width integer,
    image_height integer,
    image_updated_at timestamptz,
    raw_payload jsonb not null default '{}'::jsonb,
    unresolved_reason text,
    attempted_at timestamptz not null default current_timestamp
);

create table if not exists raw.top_artists (
    id bigserial primary key,
    artist_name text not null,
    play_count bigint not null,
    rank integer not null,
    period text not null,
    fetched_at timestamptz not null default current_timestamp,
    constraint uq_top_artists_artist_period_rank unique (artist_name, period, rank)
);

create table if not exists raw.top_tracks (
    id bigserial primary key,
    track_name text not null,
    artist_name text not null,
    play_count bigint not null,
    rank integer not null,
    period text not null,
    fetched_at timestamptz not null default current_timestamp,
    constraint uq_top_tracks_track_artist_period_rank unique (
        track_name, artist_name, period, rank
    )
);

create table if not exists raw.weather (
    id bigserial primary key,
    date date not null,
    city text not null,
    temp_c numeric,
    precipitation numeric,
    weather_code integer,
    fetched_at timestamptz not null default current_timestamp,
    constraint uq_weather_date_city unique (date, city)
);

create table if not exists raw.mood_classification_results (
    id bigserial primary key,
    track_id text not null,
    mood_label text not null,
    mood_confidence numeric not null,
    inference_seconds numeric,
    classified_at timestamptz not null default current_timestamp,
    applied_at timestamptz
);

create index if not exists idx_mood_results_pending
    on raw.mood_classification_results (track_id, classified_at desc)
    where applied_at is null;
