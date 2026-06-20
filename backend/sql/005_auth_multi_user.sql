create schema if not exists app;

create table if not exists app.users (
    id text primary key,
    lastfm_username text not null unique,
    display_name text,
    password_hash text,
    password_updated_at timestamptz,
    created_at timestamptz not null default current_timestamp,
    updated_at timestamptz not null default current_timestamp,
    last_login_at timestamptz
);

alter table app.users
    add column if not exists password_hash text;

alter table app.users
    add column if not exists password_updated_at timestamptz;

create table if not exists app.auth_sessions (
    session_token_hash text primary key,
    user_id text not null references app.users(id) on delete cascade,
    created_at timestamptz not null default current_timestamp,
    expires_at timestamptz not null,
    revoked_at timestamptz
);

create index if not exists idx_auth_sessions_user_id
    on app.auth_sessions (user_id);

create index if not exists idx_auth_sessions_expires_at
    on app.auth_sessions (expires_at);

create table if not exists app.ingestion_jobs (
    id text primary key,
    user_id text not null references app.users(id) on delete cascade,
    job_type text not null default 'lastfm_initial_import',
    status text not null,
    result jsonb not null default '{}'::jsonb,
    error_message text,
    created_at timestamptz not null default current_timestamp,
    started_at timestamptz,
    completed_at timestamptz,
    constraint chk_ingestion_jobs_status check (
        status in ('queued', 'running', 'succeeded', 'failed')
    )
);

create index if not exists idx_ingestion_jobs_user_created
    on app.ingestion_jobs (user_id, created_at desc);

create table if not exists app.user_ingestion_state (
    user_id text not null references app.users(id) on delete cascade,
    source text not null,
    last_fetched_at timestamptz not null,
    updated_at timestamptz not null default current_timestamp,
    primary key (user_id, source)
);

create table if not exists app.user_settings (
    user_id text not null references app.users(id) on delete cascade,
    key text not null,
    value text not null,
    updated_at timestamptz not null default current_timestamp,
    primary key (user_id, key)
);

insert into app.users (id, lastfm_username, display_name)
values ('legacy-single-user', 'legacy-single-user', 'Legacy Single User')
on conflict (id) do nothing;

alter table raw.raw_failed
    add column if not exists user_id text;

alter table raw.recent_tracks
    add column if not exists user_id text;

update raw.recent_tracks
set user_id = 'legacy-single-user'
where user_id is null;

alter table raw.top_artists
    add column if not exists user_id text;

update raw.top_artists
set user_id = 'legacy-single-user'
where user_id is null;

alter table raw.top_tracks
    add column if not exists user_id text;

update raw.top_tracks
set user_id = 'legacy-single-user'
where user_id is null;

insert into app.user_settings (user_id, key, value, updated_at)
select 'legacy-single-user', key, value, updated_at
from raw.user_settings
on conflict (user_id, key) do nothing;

insert into app.user_ingestion_state (user_id, source, last_fetched_at, updated_at)
select 'legacy-single-user', source, last_fetched_at, updated_at
from raw.ingestion_metadata
where source in ('lastfm_recent_tracks', 'lastfm_user_charts')
on conflict (user_id, source) do nothing;

alter table raw.recent_tracks
    alter column user_id set not null;

alter table raw.top_artists
    alter column user_id set not null;

alter table raw.top_tracks
    alter column user_id set not null;

alter table raw.recent_tracks
    drop constraint if exists uq_recent_tracks_dedupe;

alter table raw.recent_tracks
    add constraint uq_recent_tracks_dedupe unique (user_id, played_at, track_name, artist_name);

delete from raw.top_artists
where id in (
    select id
    from (
        select
            id,
            row_number() over (
                partition by user_id, period, rank
                order by fetched_at desc, id desc
            ) as row_number
        from raw.top_artists
    ) ranked
    where ranked.row_number > 1
);

alter table raw.top_artists
    drop constraint if exists uq_top_artists_artist_period_rank;

alter table raw.top_artists
    drop constraint if exists uq_top_artists_user_period_rank;

alter table raw.top_artists
    add constraint uq_top_artists_user_period_rank unique (user_id, period, rank);

delete from raw.top_tracks
where id in (
    select id
    from (
        select
            id,
            row_number() over (
                partition by user_id, period, rank
                order by fetched_at desc, id desc
            ) as row_number
        from raw.top_tracks
    ) ranked
    where ranked.row_number > 1
);

alter table raw.top_tracks
    drop constraint if exists uq_top_tracks_track_artist_period_rank;

alter table raw.top_tracks
    drop constraint if exists uq_top_tracks_user_period_rank;

alter table raw.top_tracks
    add constraint uq_top_tracks_user_period_rank unique (user_id, period, rank);

drop index if exists raw.idx_recent_tracks_played_at;

create index if not exists idx_recent_tracks_user_played_at
    on raw.recent_tracks (user_id, played_at);

do $$
begin
    if not exists (
        select 1 from pg_constraint where conname = 'fk_raw_failed_user'
    ) then
        alter table raw.raw_failed
            add constraint fk_raw_failed_user foreign key (user_id)
            references app.users(id) on delete cascade;
    end if;

    if not exists (
        select 1 from pg_constraint where conname = 'fk_recent_tracks_user'
    ) then
        alter table raw.recent_tracks
            add constraint fk_recent_tracks_user foreign key (user_id)
            references app.users(id) on delete cascade;
    end if;

    if not exists (
        select 1 from pg_constraint where conname = 'fk_top_artists_user'
    ) then
        alter table raw.top_artists
            add constraint fk_top_artists_user foreign key (user_id)
            references app.users(id) on delete cascade;
    end if;

    if not exists (
        select 1 from pg_constraint where conname = 'fk_top_tracks_user'
    ) then
        alter table raw.top_tracks
            add constraint fk_top_tracks_user foreign key (user_id)
            references app.users(id) on delete cascade;
    end if;
end $$;
