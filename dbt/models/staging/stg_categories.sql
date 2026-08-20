select
    id as category_id,
    name as category_name
from {{ source('app', 'silver_categories') }}
where id is not null
