select
    id as place_id,
    source_identifier,
    name,
    description,
    address,
    postal_code,
    city,
    region,
    country,
    contact_email,
    contact_phone,
    website,
    lat,
    lon,
    source_content_hash,
    created_at,
    updated_at,
    neo4j_synced_at,
    gold_pg_synced_at
from {{ source('app', 'silver_places') }}
where id is not null
