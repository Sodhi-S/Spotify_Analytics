alter table app.users
    add column if not exists password_hash text;

alter table app.users
    add column if not exists password_updated_at timestamptz;
