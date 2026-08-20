select
    city,
    count(*) as place_count,
    count(distinct region) as region_count,
    avg(lat) as avg_lat,
    avg(lon) as avg_lon,
    max(updated_at) as latest_place_update
from {{ ref('stg_places') }}
where city is not null
group by 1
