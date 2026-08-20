select
    p.city,
    c.category_name,
    count(distinct p.place_id) as place_count,
    avg(p.lat) as avg_lat,
    avg(p.lon) as avg_lon
from {{ ref('stg_places') }} p
join {{ ref('stg_place_categories') }} pc
    on p.place_id = pc.place_id
join {{ ref('stg_categories') }} c
    on pc.category_id = c.category_id
where p.city is not null
group by 1, 2
