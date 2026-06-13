create table if not exists raw.user_settings (
    key text primary key,
    value text not null,
    updated_at timestamptz not null default current_timestamp
);
