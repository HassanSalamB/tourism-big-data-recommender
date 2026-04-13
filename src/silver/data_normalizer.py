"""
Silver layer: normalize Postgres bronze POI documents into relational Postgres
tables and write an optional Parquet snapshot.
"""

from __future__ import annotations

import json
import os
import sys
import warnings

import pandas as pd
from psycopg2.extras import execute_values

if __package__ in (None, ""):
    # Allow running the file directly with `python src/silver/data_normalizer.py`.
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils.config import load_config
from utils.connections import conn_env


SILVER_PLACE_COLUMNS = (
    "id",
    "source_identifier",
    "name",
    "lat",
    "lon",
    "address",
    "postal_code",
    "city",
    "region",
    "country",
    "description",
    "contact_email",
    "contact_phone",
    "website",
    "source_content_hash",
)
SILVER_TEXT_COLUMNS = tuple(
    column for column in SILVER_PLACE_COLUMNS if column not in {"lat", "lon"}
)
REQUIRED_PLACE_COLUMNS = ("id", "name", "lat", "lon")


def _parse_time_series(values: pd.Series) -> pd.Series:
    # Parse time-like values with explicit formats first to avoid pandas falling back
    # to slow per-row dateutil parsing (and emitting warnings).
    raw = values.astype("string")
    parsed = pd.to_datetime(raw, format="%H:%M:%S", errors="coerce").dt.time
    missing = parsed.isna() & raw.notna()
    if missing.any():
        parsed_hm = pd.to_datetime(raw[missing], format="%H:%M", errors="coerce").dt.time
        parsed.loc[missing] = parsed_hm
        missing = parsed.isna() & raw.notna()
    if missing.any():
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=r"Could not infer format, so each element will be parsed individually.*",
                category=UserWarning,
            )
            parsed_fallback = pd.to_datetime(raw[missing], errors="coerce").dt.time
        parsed.loc[missing] = parsed_fallback
    return parsed


def _ensure_list(value):
    # DATAtourisme often uses either a single dict or a list for the same field.
    # This normalizes both shapes so downstream loops can always iterate safely.
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _query_to_dataframe(conn, query: str) -> pd.DataFrame:
    # Avoid pandas DBAPI warnings by reading through psycopg2 cursor explicitly.
    with conn.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
    return pd.DataFrame(rows, columns=columns)


def _ensure_silver_state_table(cursor):
    # Store incremental sync state so silver can read only newly updated bronze docs.
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS silver_pipeline_state (
            pipeline_name TEXT PRIMARY KEY,
            last_bronze_updated_at TIMESTAMPTZ,
            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def _get_last_bronze_watermark(cursor):
    cursor.execute(
        """
        SELECT last_bronze_updated_at
        FROM silver_pipeline_state
        WHERE pipeline_name = 'silver_normalize'
        """
    )
    row = cursor.fetchone()
    return row[0] if row else None


def _set_last_bronze_watermark(cursor, watermark):
    # The watermark limits the optional incremental scan; hash comparison still
    # remains the final proof that a bronze row changed.
    cursor.execute(
        """
        INSERT INTO silver_pipeline_state(pipeline_name, last_bronze_updated_at, updated_at)
        VALUES ('silver_normalize', %s, CURRENT_TIMESTAMP)
        ON CONFLICT (pipeline_name) DO UPDATE
        SET last_bronze_updated_at = EXCLUDED.last_bronze_updated_at,
            updated_at = CURRENT_TIMESTAMP
        """,
        (watermark,),
    )


def extract_first_text(value, preferred_langs=("fr", "en")):
    # DATAtourisme text fields can be plain strings, lists, or language dictionaries.
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        if not value:
            return None
        return extract_first_text(value[0], preferred_langs)
    if isinstance(value, dict):
        for lang in preferred_langs:
            # DATAtourisme language values are often {"fr": ["text"]}, but some
            # fields arrive as plain strings, so both shapes are accepted.
            lang_val = value.get(lang)
            if isinstance(lang_val, list) and lang_val:
                return lang_val[0]
            if isinstance(lang_val, str):
                return lang_val
    return None


def _load_extraction_rules() -> tuple[dict, dict, tuple[str, ...]]:
    # Keep fragile DATAtourisme path strings in config.yaml, not scattered through
    # Python code. If the API shape changes, update the path map there.
    extraction_config = load_config().get("silver_extraction", {})
    text_paths = extraction_config.get("text_field_paths", {})
    numeric_paths = extraction_config.get("numeric_field_paths", {})
    preferred_langs = tuple(extraction_config.get("preferred_langs", ["fr", "en"]))
    if not text_paths or not numeric_paths:
        raise ValueError(
            "Missing silver_extraction.text_field_paths/numeric_field_paths in config.yaml"
        )
    return text_paths, numeric_paths, preferred_langs


# Loaded once at import so each row does not reread config.yaml.
TEXT_FIELD_PATHS, NUMERIC_FIELD_PATHS, PREFERRED_LANGS = _load_extraction_rules()


def get_path(data, path: str):
    current = data
    for part in path.split("."):
        if isinstance(current, list):
            if not current:
                return None
            if part.isdigit():
                index = int(part)
                if index >= len(current):
                    return None
                current = current[index]
                continue
            # If the mapping does not specify an index, use the first item and
            # keep resolving the same path part against that dict.
            current = current[0]

        if isinstance(current, dict):
            current = current.get(part)
            continue

        return None
    return current


def first_value_from_paths(item, paths):
    for path in paths:
        value = get_path(item, path)
        if value is not None:
            return value
    return None


def first_text_from_paths(item, paths, preferred_langs=PREFERRED_LANGS):
    for path in paths:
        # The path map chooses where to look; extract_first_text chooses which
        # language/shape to prefer at that location.
        text = extract_first_text(get_path(item, path), preferred_langs=preferred_langs)
        if text:
            return text
    return None


def extract_fields_from_paths(item) -> dict:
    fields = {
        column: first_text_from_paths(item, paths)
        for column, paths in TEXT_FIELD_PATHS.items()
    }
    fields.update(
        {
            column: first_value_from_paths(item, paths)
            for column, paths in NUMERIC_FIELD_PATHS.items()
        }
    )
    return fields


def extract_categories(item):
    # `@type` is a list, so silver keeps every value and links them through the bridge table.
    cats = item.get("@type")
    if isinstance(cats, list):
        return [c for c in cats if isinstance(c, str)]
    if cats:
        return [cats] if isinstance(cats, str) else []
    return []


def extract_timings(item):
    # Keep all event periods so client date/time filters stay precise.
    rows = []
    fallback_start = extract_first_text(item.get("schema:startDate"))
    fallback_end = extract_first_text(item.get("schema:endDate"))

    for period in _ensure_list(item.get("takesPlaceAt")):
        if not isinstance(period, dict):
            continue
        # Some events store dates at POI level and times at period level, so we
        # combine period values with POI-level fallbacks.
        start_date = period.get("startDate") or fallback_start
        end_date = period.get("endDate") or fallback_end
        start_time = period.get("startTime")
        end_time = period.get("endTime")
        if start_date or end_date or start_time or end_time:
            rows.append((start_date, end_date, start_time, end_time))

    if not rows and (fallback_start or fallback_end):
        rows.append((fallback_start, fallback_end, None, None))
    return rows


def extract_prices(item):
    # Extract raw price values here; pandas converts them to numeric in _price_records.
    extracted = []
    for offer in _ensure_list(item.get("offers")):
        if not isinstance(offer, dict):
            continue
        for spec in _ensure_list(offer.get("schema:priceSpecification")):
            if not isinstance(spec, dict):
                continue
            min_vals = [v for v in _ensure_list(spec.get("schema:minPrice")) if v is not None]
            max_vals = [v for v in _ensure_list(spec.get("schema:maxPrice")) if v is not None]
            currency = extract_first_text(spec.get("schema:priceCurrency"))
            for min_price in min_vals or [None]:
                for max_price in max_vals or [min_price]:
                    if min_price is not None or max_price is not None or currency:
                        extracted.append((min_price, max_price, currency))

    unique_rows = []
    seen = set()
    for row in extracted:
        if row in seen:
            continue
        seen.add(row)
        unique_rows.append(row)
    return unique_rows


def _validate_table_columns(cursor, table_name: str, expected_columns: dict[str, str]):
    cursor.execute(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        """,
        (table_name,),
    )
    actual_columns = dict(cursor.fetchall())
    problems = []
    for column_name, expected_type in expected_columns.items():
        actual_type = actual_columns.get(column_name)
        if actual_type is None:
            problems.append(f"{table_name}.{column_name} is missing")
        elif actual_type != expected_type:
            problems.append(
                f"{table_name}.{column_name} expected {expected_type}, found {actual_type}"
            )
    if problems:
        # This is intentionally strict: wrong existing column types can silently
        # corrupt cleaning/output, so the user should rebuild or migrate the table.
        raise ValueError("Silver schema mismatch: " + "; ".join(problems))


def _validate_silver_schema(cursor):
    _validate_table_columns(
        cursor,
        "silver_places",
        {
            "id": "text",
            "source_identifier": "text",
            "name": "text",
            "lat": "double precision",
            "lon": "double precision",
            "address": "text",
            "postal_code": "text",
            "city": "text",
            "region": "text",
            "country": "text",
            "description": "text",
            "contact_email": "text",
            "contact_phone": "text",
            "website": "text",
            "source_content_hash": "text",
            "created_at": "timestamp without time zone",
            "updated_at": "timestamp without time zone",
            "neo4j_synced_at": "timestamp without time zone",
            "gold_pg_synced_at": "timestamp without time zone",
        },
    )
    _validate_table_columns(
        cursor,
        "silver_prices",
        {
            "place_id": "text",
            "min_price": "numeric",
            "max_price": "numeric",
            "currency": "text",
        },
    )
    _validate_table_columns(
        cursor,
        "silver_timings",
        {
            "place_id": "text",
            "start_date": "date",
            "end_date": "date",
            "start_time": "time without time zone",
            "end_time": "time without time zone",
        },
    )


def _ensure_silver_tables(cursor):
    # Silver reshapes raw JSON into relational tables that are easier to query downstream.
    cursor.execute(
        """
        DO $$
        BEGIN
            -- Keep old local table names compatible with the current names.
            IF to_regclass('public.silver_place_timings') IS NOT NULL
               AND to_regclass('public.silver_timings') IS NULL THEN
                ALTER TABLE silver_place_timings RENAME TO silver_timings;
            END IF;
            IF to_regclass('public.silver_place_prices') IS NOT NULL
               AND to_regclass('public.silver_prices') IS NULL THEN
                ALTER TABLE silver_place_prices RENAME TO silver_prices;
            END IF;
        END$$;
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS silver_places (
            id TEXT PRIMARY KEY,
            source_identifier TEXT,
            name TEXT,
            lat DOUBLE PRECISION,
            lon DOUBLE PRECISION,
            address TEXT,
            postal_code TEXT,
            city TEXT,
            region TEXT,
            country TEXT,
            description TEXT,
            contact_email TEXT,
            contact_phone TEXT,
            website TEXT,
            source_content_hash TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            neo4j_synced_at TIMESTAMP,
            gold_pg_synced_at TIMESTAMP
        )
        """
    )
    cursor.execute(
        "ALTER TABLE silver_places ADD COLUMN IF NOT EXISTS source_identifier TEXT"
    )
    cursor.execute(
        "ALTER TABLE silver_places ADD COLUMN IF NOT EXISTS source_content_hash TEXT"
    )
    cursor.execute("ALTER TABLE silver_places ADD COLUMN IF NOT EXISTS postal_code TEXT")
    cursor.execute("ALTER TABLE silver_places ADD COLUMN IF NOT EXISTS region TEXT")
    cursor.execute("ALTER TABLE silver_places ADD COLUMN IF NOT EXISTS contact_email TEXT")
    cursor.execute("ALTER TABLE silver_places ADD COLUMN IF NOT EXISTS contact_phone TEXT")
    cursor.execute("ALTER TABLE silver_places ADD COLUMN IF NOT EXISTS website TEXT")
    cursor.execute(
        "ALTER TABLE silver_places ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
    )
    cursor.execute(
        "ALTER TABLE silver_places ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
    )
    cursor.execute(
        "ALTER TABLE silver_places ADD COLUMN IF NOT EXISTS neo4j_synced_at TIMESTAMP"
    )
    cursor.execute(
        "ALTER TABLE silver_places ADD COLUMN IF NOT EXISTS gold_pg_synced_at TIMESTAMP"
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS silver_categories (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS silver_place_categories (
            place_id TEXT REFERENCES silver_places(id),
            category_id INTEGER REFERENCES silver_categories(id),
            PRIMARY KEY (place_id, category_id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS silver_timings (
            timing_id BIGSERIAL PRIMARY KEY,
            place_id TEXT REFERENCES silver_places(id) ON DELETE CASCADE,
            start_date DATE,
            end_date DATE,
            start_time TIME,
            end_time TIME,
            UNIQUE (place_id, start_date, end_date, start_time, end_time)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS silver_prices (
            price_id BIGSERIAL PRIMARY KEY,
            place_id TEXT REFERENCES silver_places(id) ON DELETE CASCADE,
            min_price NUMERIC,
            max_price NUMERIC,
            currency TEXT,
            UNIQUE (place_id, min_price, max_price, currency)
        )
        """
    )
    # Indexes tuned for common client filters: location + date + budget + categories.
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_silver_places_city ON silver_places(city)")
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_silver_places_region ON silver_places(region)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_silver_places_lat_lon ON silver_places(lat, lon)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_silver_places_source_identifier ON silver_places(source_identifier)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_silver_timings_place_dates "
        "ON silver_timings(place_id, start_date, end_date)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_silver_prices_place_budget "
        "ON silver_prices(place_id, min_price, max_price)"
    )
    _validate_silver_schema(cursor)


def _upsert_places(cursor, place_batch):
    if not place_batch:
        return
    insert_columns = ",\n            ".join(SILVER_PLACE_COLUMNS)
    update_columns = [column for column in SILVER_PLACE_COLUMNS if column != "id"]
    update_assignments = ",\n            ".join(
        f"{column} = EXCLUDED.{column}" for column in update_columns
    )
    # Upsert lets silver refresh only the POIs that changed in bronze.
    execute_values(
        cursor,
        f"""
        INSERT INTO silver_places(
            {insert_columns}
        )
        VALUES %s
        ON CONFLICT (id) DO UPDATE
        SET {update_assignments},
            updated_at = CURRENT_TIMESTAMP
        """,
        place_batch,
    )


def _replace_category_links(cursor, category_links, place_ids):
    if place_ids:
        # Changed POIs get their category links rebuilt from scratch so stale links disappear.
        cursor.execute(
            "DELETE FROM silver_place_categories WHERE place_id = ANY(%s)",
            (place_ids,),
        )
    if category_links:
        execute_values(
            cursor,
            """
            INSERT INTO silver_place_categories(place_id, category_id)
            VALUES %s
            ON CONFLICT DO NOTHING
            """,
            category_links,
        )


def _replace_timing_rows(cursor, timing_rows, place_ids):
    if place_ids:
        cursor.execute(
            "DELETE FROM silver_timings WHERE place_id = ANY(%s)",
            (place_ids,),
        )
    if timing_rows:
        execute_values(
            cursor,
            """
            INSERT INTO silver_timings(place_id, start_date, end_date, start_time, end_time)
            VALUES %s
            ON CONFLICT DO NOTHING
            """,
            timing_rows,
        )


def _replace_price_rows(cursor, price_rows, place_ids):
    if place_ids:
        cursor.execute(
            "DELETE FROM silver_prices WHERE place_id = ANY(%s)",
            (place_ids,),
        )
    if price_rows:
        execute_values(
            cursor,
            """
            INSERT INTO silver_prices(place_id, min_price, max_price, currency)
            VALUES %s
            ON CONFLICT DO NOTHING
            """,
            price_rows,
        )


def _delete_rejected_places(cursor, place_ids):
    if not place_ids:
        return
    # If a row was previously accepted but now fails silver cleaning, remove it
    # so gold can trust that `silver_places` only contains usable POIs.
    cursor.execute(
        "DELETE FROM silver_place_categories WHERE place_id = ANY(%s)",
        (place_ids,),
    )
    cursor.execute(
        "DELETE FROM silver_places WHERE id = ANY(%s)",
        (place_ids,),
    )


def _cleanup_orphan_categories(cursor):
    # If a category is no longer linked to any POI, remove it from the lookup table.
    cursor.execute(
        """
        DELETE FROM silver_categories c
        WHERE NOT EXISTS (
            SELECT 1
            FROM silver_place_categories pc
            WHERE pc.category_id = c.id
        )
        """
    )


def _write_silver_parquet(conn, parquet_output: str):
    # Parquet is optional: it gives the team a portable analytics snapshot of silver.
    query = """
    SELECT
        p.id,
        p.source_identifier,
        p.name,
        p.lat,
        p.lon,
        p.address,
        p.postal_code,
        p.city,
        p.region,
        p.country,
        p.description,
        p.contact_email,
        p.contact_phone,
        p.website,
        MIN(t.start_date) AS start_date,
        MAX(t.end_date) AS end_date,
        MIN(pr.min_price) AS min_price,
        MAX(pr.max_price) AS max_price,
        MAX(pr.currency) FILTER (WHERE pr.currency IS NOT NULL) AS currency,
        COALESCE(
            ARRAY_AGG(DISTINCT c.name) FILTER (WHERE c.name IS NOT NULL),
            ARRAY[]::TEXT[]
        ) AS categories
    FROM silver_places p
    LEFT JOIN silver_place_categories pc ON p.id = pc.place_id
    LEFT JOIN silver_categories c ON pc.category_id = c.id
    LEFT JOIN silver_timings t ON p.id = t.place_id
    LEFT JOIN silver_prices pr ON p.id = pr.place_id
    GROUP BY
        p.id,
        p.source_identifier,
        p.name,
        p.lat,
        p.lon,
        p.address,
        p.postal_code,
        p.city,
        p.region,
        p.country,
        p.description,
        p.contact_email,
        p.contact_phone,
        p.website
    ORDER BY p.id
    """
    _query_to_dataframe(conn, query).to_parquet(parquet_output, index=False)


def _bronze_table_exists(cursor) -> bool:
    cursor.execute("SELECT to_regclass('public.bronze_raw_poi')")
    return cursor.fetchone()[0] is not None


def _bronze_change_filter(last_bronze_watermark, test_mode: bool):
    # Hash comparison is the main incremental rule: only missing or changed raw
    # payloads should be normalized into silver.
    filters = [
        "(s.id IS NULL OR s.source_content_hash IS DISTINCT FROM b.content_hash)"
    ]
    params = []
    if last_bronze_watermark is not None and not test_mode:
        # Watermark narrows the scan after the first full run, but does not
        # replace the hash comparison above.
        filters.append("b.updated_at > %s")
        params.append(last_bronze_watermark)
    return filters, params


def _rows_to_dataframe(rows) -> pd.DataFrame:
    return pd.DataFrame(
        rows,
        columns=["id", "source_identifier", "raw_payload", "content_hash", "updated_at"],
    )


def _stream_changed_bronze_chunks(
    conn,
    last_bronze_watermark,
    test_mode: bool,
    test_limit: int,
    batch_size: int,
):
    filters, params = _bronze_change_filter(last_bronze_watermark, test_mode)

    limit_clause = ""
    if test_mode:
        limit_clause = "LIMIT %s"
        params.append(test_limit)

    query = f"""
        SELECT
            b.id,
            b.source_identifier,
            b.raw_payload,
            b.content_hash,
            b.updated_at
        FROM bronze_raw_poi b
        LEFT JOIN silver_places s ON s.id = b.id
        WHERE {" AND ".join(filters)}
        ORDER BY b.updated_at
        {limit_clause}
    """

    with conn.cursor(name="silver_bronze_stream") as stream:
        stream.itersize = batch_size
        stream.execute(query, params)
        while True:
            # `fetchmany` gives pandas bounded chunks instead of materializing all bronze rows.
            rows = stream.fetchmany(batch_size)
            if not rows:
                break
            yield _rows_to_dataframe(rows)


def _as_plain_object(value):
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            # JSONB normally arrives as dict through psycopg2, but direct tests
            # or future drivers may provide a JSON string.
            loaded = json.loads(value)
            return loaded if isinstance(loaded, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _clean_text_series(series: pd.Series) -> pd.Series:
    # Central pandas text cleanup: trim whitespace and store empty strings as SQL NULL.
    return (
        series.astype("string")
        .str.strip()
        .replace({"": pd.NA, "None": pd.NA, "nan": pd.NA})
        .astype(object)
    )


def _to_db_records(df: pd.DataFrame, columns: list[str]) -> list[tuple]:
    if df.empty:
        return []
    # psycopg2 expects Python None for NULL, not pandas NA/NaN sentinel values.
    output = df.loc[:, columns].astype(object).where(pd.notna(df.loc[:, columns]), None)
    return list(output.itertuples(index=False, name=None))


def _normalize_places_chunk(
    bronze_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if bronze_df.empty:
        empty = pd.DataFrame()
        return empty, pd.Series(dtype=object), empty, empty, empty

    raw_items = bronze_df["raw_payload"].map(_as_plain_object)
    extracted_fields = pd.DataFrame(raw_items.map(extract_fields_from_paths).tolist())
    extracted_fields["source_identifier"] = extracted_fields["source_identifier"].fillna(
        bronze_df["source_identifier"]
    )
    # The JSON selectors map nested ontology fields into flat columns; pandas then
    # handles type conversion, null cleanup, dedupe, and exploded child tables.
    extracted = pd.DataFrame(
        {
            "id": bronze_df["id"],
            "source_identifier": extracted_fields["source_identifier"],
            "name": extracted_fields["name"],
            "lat": extracted_fields["lat"],
            "lon": extracted_fields["lon"],
            "address": extracted_fields["address"],
            "postal_code": extracted_fields["postal_code"],
            "city": extracted_fields["city"],
            "region": extracted_fields["region"],
            "country": extracted_fields["country"],
            "description": extracted_fields["description"],
            "contact_email": extracted_fields["contact_email"],
            "contact_phone": extracted_fields["contact_phone"],
            "website": extracted_fields["website"],
            "categories": raw_items.map(extract_categories),
            "timings": raw_items.map(extract_timings),
            "prices": raw_items.map(extract_prices),
            "source_content_hash": bronze_df["content_hash"],
            "bronze_updated_at": bronze_df["updated_at"],
        }
    )

    extracted[list(SILVER_TEXT_COLUMNS)] = extracted[list(SILVER_TEXT_COLUMNS)].apply(
        _clean_text_series
    )
    extracted["lat"] = pd.to_numeric(extracted["lat"], errors="coerce")
    extracted["lon"] = pd.to_numeric(extracted["lon"], errors="coerce")
    # Invalid coordinate ranges are rejected in silver so gold can trust the data.
    valid_coordinates = extracted["lat"].between(-90, 90) & extracted["lon"].between(-180, 180)

    cleaned_places = (
        extracted.loc[valid_coordinates]
        .dropna(subset=list(REQUIRED_PLACE_COLUMNS))
        .drop_duplicates(subset=["id"], keep="last")
        .reset_index(drop=True)
    )
    changed_ids = cleaned_places["id"].copy()

    return (
        cleaned_places.loc[:, list(SILVER_PLACE_COLUMNS)],
        changed_ids,
        cleaned_places.loc[:, ["id", "categories"]],
        cleaned_places.loc[:, ["id", "timings"]],
        cleaned_places.loc[:, ["id", "prices"]],
    )


def _get_category_ids(cursor, category_names) -> dict[str, int]:
    names = pd.Series(category_names, dtype="object").dropna().drop_duplicates().tolist()
    if not names:
        return {}
    execute_values(
        cursor,
        """
        INSERT INTO silver_categories(name)
        VALUES %s
        ON CONFLICT (name) DO NOTHING
        """,
        [(name,) for name in names],
    )
    # Fetch ids after the upsert because existing categories do not return ids from DO NOTHING.
    cursor.execute("SELECT name, id FROM silver_categories WHERE name = ANY(%s)", (names,))
    return dict(cursor.fetchall())


def _category_link_records(cursor, categories_df: pd.DataFrame) -> list[tuple]:
    if categories_df.empty:
        return []
    links = categories_df.explode("categories").rename(columns={"categories": "category"})
    links["category"] = _clean_text_series(links["category"])
    # A POI can have many category strings; exact duplicates are removed before linking.
    links = links.dropna(subset=["id", "category"]).drop_duplicates(subset=["id", "category"])
    category_ids = _get_category_ids(cursor, links["category"])
    links["category_id"] = links["category"].map(category_ids)
    links = links.dropna(subset=["category_id"])
    links["category_id"] = links["category_id"].astype("int64")
    return _to_db_records(links, ["id", "category_id"])


def _timing_records(timings_df: pd.DataFrame) -> list[tuple]:
    if timings_df.empty:
        return []
    timings = timings_df.explode("timings").dropna(subset=["timings"])
    if timings.empty:
        return []
    timing_values = pd.DataFrame(
        timings["timings"].tolist(),
        index=timings.index,
        columns=["start_date", "end_date", "start_time", "end_time"],
    )
    timings = pd.concat([timings[["id"]], timing_values], axis=1)
    # Coerce bad dates/times to NaT, then drop rows where every timing field is missing.
    timings["start_date"] = pd.to_datetime(timings["start_date"], errors="coerce").dt.date
    timings["end_date"] = pd.to_datetime(timings["end_date"], errors="coerce").dt.date
    timings["start_time"] = _parse_time_series(timings["start_time"])
    timings["end_time"] = _parse_time_series(timings["end_time"])
    timings = timings.dropna(
        subset=["start_date", "end_date", "start_time", "end_time"],
        how="all",
    )
    timings = timings.drop_duplicates(
        subset=["id", "start_date", "end_date", "start_time", "end_time"]
    )
    return _to_db_records(timings, ["id", "start_date", "end_date", "start_time", "end_time"])


def _price_records(prices_df: pd.DataFrame) -> list[tuple]:
    if prices_df.empty:
        return []
    prices = prices_df.explode("prices").dropna(subset=["prices"])
    if prices.empty:
        return []
    price_values = pd.DataFrame(
        prices["prices"].tolist(),
        index=prices.index,
        columns=["min_price", "max_price", "currency"],
    )
    prices = pd.concat([prices[["id"]], price_values], axis=1)
    # Prices are stored as NUMERIC in Postgres, so invalid strings become NULL here.
    prices["min_price"] = pd.to_numeric(prices["min_price"], errors="coerce")
    prices["max_price"] = pd.to_numeric(prices["max_price"], errors="coerce")
    prices["max_price"] = prices["max_price"].fillna(prices["min_price"])
    prices["currency"] = _clean_text_series(prices["currency"])
    prices = prices.dropna(subset=["min_price", "max_price", "currency"], how="all")
    prices = prices.groupby(["id", "currency"], dropna=False, as_index=False).agg(
        min_price=("min_price", "min"),
        max_price=("max_price", "max"),
    )
    prices = prices.drop_duplicates(subset=["id", "min_price", "max_price", "currency"])
    return _to_db_records(prices, ["id", "min_price", "max_price", "currency"])


def run_silver_normalize(
    parquet_output: str,
    test_mode: bool = True,
    test_limit: int = 5000,
    batch_size: int = 1000,
):
    """Normalize only new/changed bronze records into silver tables."""
    os.makedirs(os.path.dirname(parquet_output) or ".", exist_ok=True)
    print("[Pipeline] Silver normalize: start")

    conn = conn_env()
    read_conn = None
    cursor = conn.cursor()
    try:
        _ensure_silver_tables(cursor)
        _ensure_silver_state_table(cursor)
        conn.commit()

        if not _bronze_table_exists(cursor):
            print("[Silver] Skip: bronze_raw_poi table does not exist yet.")
            return

        last_bronze_watermark = _get_last_bronze_watermark(cursor)
        if last_bronze_watermark is not None and not test_mode:
            print(f"[Silver] Incremental read enabled from bronze watermark: {last_bronze_watermark}")
        elif test_mode:
            print(f"[Silver] Test mode: reading up to {test_limit} changed bronze rows.")
        else:
            print("[Silver] Full bronze comparison mode (no watermark yet).")

        normalized = 0
        scanned = 0
        max_bronze_updated_at = last_bronze_watermark
        read_conn = conn_env()

        for bronze_df in _stream_changed_bronze_chunks(
            read_conn,
            last_bronze_watermark,
            test_mode,
            test_limit,
            batch_size,
        ):
            scanned += len(bronze_df)
            chunk_max_updated_at = bronze_df["updated_at"].dropna().max()
            if pd.notna(chunk_max_updated_at):
                # Track the newest bronze timestamp successfully seen so the next run
                # can start from that watermark in non-test mode.
                if max_bronze_updated_at is None or chunk_max_updated_at > max_bronze_updated_at:
                    max_bronze_updated_at = chunk_max_updated_at

            try:
                (
                    places_df,
                    changed_ids,
                    categories_df,
                    timings_df,
                    prices_df,
                ) = _normalize_places_chunk(bronze_df)

                place_records = _to_db_records(
                    places_df,
                    list(SILVER_PLACE_COLUMNS),
                )
                changed_place_ids = changed_ids.dropna().drop_duplicates().tolist()
                source_place_ids = (
                    _clean_text_series(bronze_df["id"]).dropna().drop_duplicates().tolist()
                )
                # If pandas cleaning rejects an id, delete any older accepted copy from silver.
                rejected_place_ids = sorted(set(source_place_ids) - set(changed_place_ids))

                _delete_rejected_places(cursor, rejected_place_ids)
                _upsert_places(cursor, place_records)
                _replace_category_links(
                    cursor,
                    _category_link_records(cursor, categories_df),
                    changed_place_ids,
                )
                _replace_timing_rows(cursor, _timing_records(timings_df), changed_place_ids)
                _replace_price_rows(cursor, _price_records(prices_df), changed_place_ids)
                conn.commit()

                normalized += len(place_records)
                print(
                    f"[Silver] Read {scanned} changed bronze rows "
                    f"(normalized: {normalized})"
                )
            except Exception as exc:
                conn.rollback()
                print(f"[Silver] Error normalizing pandas chunk ending at row {scanned}: {exc}")

        _cleanup_orphan_categories(cursor)
        if not test_mode and max_bronze_updated_at is not None:
            _set_last_bronze_watermark(cursor, max_bronze_updated_at)
        conn.commit()

        _write_silver_parquet(conn, parquet_output)
        print(f"[Silver] DONE: {normalized} changed POIs normalized -> {parquet_output}")
    finally:
        conn.close()
        if read_conn is not None:
            read_conn.close()

    print("[Pipeline] Silver normalize: done")


if __name__ == "__main__":
    cfg = load_config()
    run_silver_normalize(
        parquet_output=cfg.get(
            "db_paths", {}
        ).get("parquet_output", "data/silver/parquet/places.parquet"),
        test_mode=True,
        test_limit=5000,
        batch_size=int(cfg.get("api", {}).get("batch_size", 1000)),
    )
