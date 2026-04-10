import os
import json
import pandas as pd
from psycopg2.extras import execute_values
from db import get_connection


# Change paths according to your project

BRONZE_PATH = r"D:\holiday_project\data\bronze\datatourisme\objects"
PARQUET_OUTPUT = r"D:\holiday_project\data\silver\parquet\places.parquet"


# test mode is included to run small batches of files to check if script is running ok
# change to False to run script on complete dataset
TEST_MODE = True
TEST_LIMIT = 5000
BATCH_SIZE = 1000

os.makedirs(os.path.dirname(PARQUET_OUTPUT), exist_ok=True)


# DB CONNECTION
# -----------------------------
conn = get_connection()
cursor = conn.cursor()


# CREATE TABLE
# -----------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS places (
    id TEXT PRIMARY KEY,
    name TEXT,
    lat DOUBLE PRECISION,
    lon DOUBLE PRECISION,
    address TEXT,
    city TEXT,
    country TEXT,
    description TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS place_categories (
    place_id TEXT,
    category_id INTEGER,
    PRIMARY KEY (place_id, category_id)
)
""")

conn.commit()


# HELPERS
# -----------------------------
def extract_name(item):
    return extract_first_text(item.get("rdfs:label"))


def extract_geo(item):
    try:
        locations = item.get("isLocatedAt", [])
        if not locations:
            return None, None

        geo = locations[0].get("schema:geo", {})
        lat = geo.get("schema:latitude")
        lon = geo.get("schema:longitude")

        if lat and lon:
            return float(lat), float(lon)
    except:
        pass
    return None, None


def extract_first_text(value, preferred_langs=("en", "fr")):
    if value is None:
        return None

    if isinstance(value, str):
        return value

    if isinstance(value, list):
        if not value:
            return None
        first = value[0]
        return extract_first_text(first, preferred_langs)

    if isinstance(value, dict):
        for lang in preferred_langs:
            lang_val = value.get(lang)
            if isinstance(lang_val, list) and lang_val:
                return lang_val[0]
            if isinstance(lang_val, str):
                return lang_val

    return None


def extract_address(item):
    try:
        locations = item.get("isLocatedAt", [])
        if not locations or not isinstance(locations, list):
            return None, None, None

        first_location = locations[0]
        addresses = first_location.get("schema:address", [])

        if isinstance(addresses, list):
            if not addresses:
                return None, None, None
            address = addresses[0]
        elif isinstance(addresses, dict):
            address = addresses
        else:
            return None, None, None

        street = extract_first_text(address.get("schema:streetAddress"))

        city = None
        city_data = address.get("hasAddressCity")
        if isinstance(city_data, dict):
            city = extract_first_text(city_data.get("rdfs:label"))

        if not city:
            city = extract_first_text(address.get("schema:addressLocality"))

        country = extract_first_text(address.get("schema:addressCountry"))

        if not country and isinstance(city_data, dict):
            dept = city_data.get("isPartOfDepartment", {})
            region = dept.get("isPartOfRegion", {}) if isinstance(dept, dict) else {}
            country_data = region.get("isPartOfCountry", {}) if isinstance(region, dict) else {}
            if isinstance(country_data, dict):
                country = extract_first_text(country_data.get("rdfs:label"))

        return street, city, country

    except Exception:
        return None, None, None


def extract_description(item):
    desc = item.get("owl:topObjectProperty")
    if isinstance(desc, dict):
        return desc.get("fr", [None])[0]
    return None


def extract_categories(item):
    cats = item.get("@type")
    if isinstance(cats, list):
        return cats
    elif cats:
        return [cats]
    return []


def get_category_id(cat_name):
    cursor.execute(
        "INSERT INTO categories(name) VALUES (%s) ON CONFLICT DO NOTHING",
        (cat_name,)
    )
    cursor.execute(
        "SELECT id FROM categories WHERE name = %s",
        (cat_name,)
    )
    return cursor.fetchone()[0]


# FILE COLLECTION
# -----------------------------
json_files = []

for root, _, files in os.walk(BRONZE_PATH):
    for file in files:
        if file.endswith(".json"):
            json_files.append(os.path.join(root, file))

if TEST_MODE:
    json_files = json_files[:TEST_LIMIT]

total_files = len(json_files)
print(f"Processing {total_files} files")

# -----------------------------
# BUFFERS
# -----------------------------
place_batch = []
category_links = []
parquet_data = []

processed = 0


# PROCESSING LOOP
# -----------------------------
for i, file_path in enumerate(json_files, start=1):
    try:
        with open(file_path, encoding="utf-8") as f:
            item = json.load(f)

        if not isinstance(item, dict):
            continue

        place_id = item.get("@id")
        name = extract_name(item)
        lat, lon = extract_geo(item)
        street, city, country = extract_address(item)
        description = extract_description(item)
        categories = extract_categories(item)

        if not place_id or not lat or not lon:
            continue

        
        # Add place
        # -------------------------
        place_batch.append((
            place_id, name, lat, lon,
            street, city, country, description
        ))

        
        # Categories
        # -------------------------
        for cat in categories:
            cid = get_category_id(cat)
            category_links.append((place_id, cid))

        
        # Parquet
        # -------------------------
        parquet_data.append({
            "id": place_id,
            "name": name,
            "lat": lat,
            "lon": lon,
            "city": city,
            "country": country,
            "category": categories
        })

        processed += 1

        
        # Batch insert
        # -------------------------
        if len(place_batch) >= BATCH_SIZE:
            execute_values(cursor, """
                INSERT INTO places(id, name, lat, lon, address, city, country, description)
                VALUES %s
                ON CONFLICT DO NOTHING
            """, place_batch)

            execute_values(cursor, """
                INSERT INTO place_categories(place_id, category_id)
                VALUES %s
                ON CONFLICT DO NOTHING
            """, category_links)

            conn.commit()
            place_batch.clear()
            category_links.clear()

        # Progress
        if i % 1000 == 0:
            print(f"Processed {i}/{total_files}")

    except Exception as e:
        print(f" Error: {file_path} | {e}")
        continue

# -----------------------------
# FINAL FLUSH
# -----------------------------
if place_batch:
    execute_values(cursor, """
        INSERT INTO places(id, name, lat, lon, address, city, country, description)
        VALUES %s
        ON CONFLICT DO NOTHING
    """, place_batch)

if category_links:
    execute_values(cursor, """
        INSERT INTO place_categories(place_id, category_id)
        VALUES %s
        ON CONFLICT DO NOTHING
    """, category_links)

conn.commit()
conn.close()


# PARQUET OUTPUT
# -----------------------------
df = pd.DataFrame(parquet_data)
df.to_parquet(PARQUET_OUTPUT, index=False)

print(f"\n DONE: {processed} POIs processed")