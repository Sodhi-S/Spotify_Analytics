{% snapshot artists_snapshot %}

{{
    config(
        target_schema=target.schema,
        unique_key='artist_id',
        strategy='check',
        check_cols=['listener_count', 'play_count', 'genres']
    )
}}

select * from {{ ref('int_artists_snapshot') }}

{% endsnapshot %}
