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
