create table if not exists raw.track_emotion_features (
    track_id text primary key,
    valence_raw numeric,
    arousal_raw numeric,
    valence numeric,
    energy numeric,
    mood_label text,
    predicted_moods jsonb not null default '[]'::jsonb,
    model_name text not null,
    model_version text,
    source_audio_url text,
    inference_seconds numeric,
    classified_at timestamptz not null default current_timestamp,
    error_message text
);

create index if not exists idx_track_emotion_features_classified_at
    on raw.track_emotion_features (classified_at desc);
