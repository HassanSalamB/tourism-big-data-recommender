select
    place_id,
    category_id
from {{ source('app', 'silver_place_categories') }}
where place_id is not null
  and category_id is not null
