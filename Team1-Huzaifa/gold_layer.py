import pandas as pd
import h3
from db import get_connection

print("Running GOLD LAYER SCRIPT")

# CONFIG

H3_RESOLUTION = 8  

# CONNECT TO DB

conn = get_connection()
cursor = conn.cursor()

cursor.execute("SELECT current_database();")
print("Connected to DB:", cursor.fetchone()[0])


# LOAD DATA FROM SILVER LAYER

print("Loading data...")

query = """
SELECT 
    p.id,
    p.name,
    p.lat,
    p.lon,
    p.city,
    c.name AS category
FROM places p
LEFT JOIN place_categories pc ON p.id = pc.place_id
LEFT JOIN categories c ON pc.category_id = c.id
WHERE p.lat IS NOT NULL 
  AND p.lon IS NOT NULL
  AND p.name IS NOT NULL
"""

df = pd.read_sql(query, conn)

print(f" Loaded {len(df)} rows")


# BASIC CLEANING

df = df.dropna(subset=["lat", "lon", "name"])
df = df.drop_duplicates(subset=["id", "category"])

print("\n Data quality check:")
print("Total rows:", len(df))


if df.empty:
    print("No usable rows found in Silver layer.")
    conn.close()
    raise SystemExit


# ADD H3 INDEX

print("Computing H3 index...")

df["h3_index"] = df.apply(
    lambda row: h3.latlng_to_cell(row["lat"], row["lon"], H3_RESOLUTION),
    axis=1
)


# SIMPLE SCORING

def compute_score(row):
    score = 1
    category = row["category"]

    if isinstance(category, str):
        cat = category.lower()

        if "museum" in cat:
            score += 3
        elif "park" in cat:
            score += 2
        elif "restaurant" in cat:
            score += 1
        elif "heritage" in cat:
            score += 2
        elif "cultural" in cat:
            score += 2

    return score

df["score"] = df.apply(compute_score, axis=1)


# CREATE CLUSTERS

print("Creating clusters...")

clusters = (
    df.groupby("h3_index")
    .agg({
        "id": lambda x: list(set(x)),
        "name": lambda x: list(dict.fromkeys(x)),
        "category": lambda x: list(set([c for c in x if pd.notna(c)])),
        "score": "sum",
        "city": lambda x: x.dropna().iloc[0] if not x.dropna().empty else None
    })
    .reset_index()
)

clusters["poi_count"] = clusters["name"].apply(len)

# keep only richer clusters
clusters = clusters[clusters["poi_count"] >= 2]

# sort by best clusters first
clusters = clusters.sort_values(
    by=["score", "poi_count"],
    ascending=[False, False]
)

print(f" Created {len(clusters)} clusters")


# SAVE GOLD TABLE

print("Saving data to PostgreSQL...")

cursor.execute("""
CREATE TABLE IF NOT EXISTS gold_clusters (
    h3_index TEXT PRIMARY KEY,
    city TEXT,
    total_score FLOAT,
    poi_count INTEGER
)
""")

# cleanup so reruns refresh values
cursor.execute("TRUNCATE TABLE gold_clusters")

for _, row in clusters.iterrows():
    cursor.execute("""
    INSERT INTO gold_clusters (h3_index, city, total_score, poi_count)
    VALUES (%s, %s, %s, %s)
    """, (
        row["h3_index"],
        row["city"],
        row["score"],
        row["poi_count"]
    ))

conn.commit()


# PICK BEST SAMPLE CITY

city_counts = df["city"].dropna().value_counts()

if city_counts.empty:
    print("No valid city found in dataset")
    sample_city = None
else:
    sample_city = city_counts.index[0]

print("\n Generating sample itinerary...\n")
print(f" City selected: {sample_city}\n")


# ITINERARY GENERATOR

def generate_itinerary(city, days=3, max_places_per_day=5):
    """
    Build a simple itinerary by selecting top H3 clusters in a city.
    Each selected cluster becomes one day block.
    """
    if city is None:
        print("No city provided for itinerary generation.")
        return []

    city_clusters = clusters[clusters["city"] == city]

    if city_clusters.empty:
        print(f" No data for city: {city}")
        return []

    top_clusters = city_clusters.head(days)

    itinerary = []

    for i, (_, row) in enumerate(top_clusters.iterrows(), start=1):
        itinerary.append({
            "day": i,
            "area": row["h3_index"],
            "poi_count": row["poi_count"],
            "places": row["name"][:max_places_per_day]
        })

    return itinerary


# RUN SAMPLE ITINERARY

itinerary = generate_itinerary(sample_city, days=3, max_places_per_day=5)

if not itinerary:
    print("No itinerary could be generated.")
else:
    for day in itinerary:
        print(f"Day {day['day']}:")
        print(f"Area: {day['area']} | POIs in cluster: {day['poi_count']}")
        for place in day["places"]:
            print(" -", place)
        print()


# OPTIONAL: SHOW TOP CITIES

print("Top cities by POI count:")
print(city_counts.head(10))


# CLOSE

conn.close()

print("\n Gold layer completed successfully")
