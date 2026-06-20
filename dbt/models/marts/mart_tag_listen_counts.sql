select
    listens.user_id,
    listens.date_id,
    artist_tags.tag_name as tag,
    count(*) as listen_count
from {{ ref('fact_listens') }} listens
join {{ ref('stg_artist_tags') }} artist_tags
    on listens.artist_id = artist_tags.artist_id
where artist_tags.tag_name is not null
group by
    listens.user_id,
    listens.date_id,
    artist_tags.tag_name
