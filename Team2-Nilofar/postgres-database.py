import zipfile
import json
import psycopg2
from io import TextIOWrapper

#----Setting----
ZIP_FILE = "flux-25818-202603141313.zip"
DB_CONFIG = {
    "dbname": "dst_db",
    "user": "daniel",
    "password": "datascientest", 
    "host": "localhost",
    "port": "5432"
}

def setup_database():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    print("Cleaning and setting up Postgres tables...")
    cur.execute("DROP TABLE IF EXISTS pois CASCADE;")
    cur.execute("DROP TABLE IF EXISTS categories CASCADE;")
    

    cur.execute("""
        CREATE TABLE categories (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) UNIQUE
        );
    """)
    

    cur.execute("""
        CREATE TABLE pois (
            id SERIAL PRIMARY KEY,
            label TEXT,
            category_id INTEGER REFERENCES categories(id),
            city VARCHAR(255),
            latitude DOUBLE PRECISION,
            longitude DOUBLE PRECISION,
            rating REAL,
            last_update VARCHAR(100)
        );
    """)
    
    conn.commit()
    return conn, cur

def get_or_create_category(cur, cat_name):
    cur.execute("SELECT id FROM categories WHERE name = %s", (cat_name,))
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute("INSERT INTO categories (name) VALUES (%s) RETURNING id", (cat_name,))
    return cur.fetchone()[0]


def extract_geo(item):
    loc = item.get("isLocatedAt", [{}])
    if isinstance(loc, list) and len(loc) > 0: loc = loc[0]
    geo = loc.get("schema:geo", {}) if isinstance(loc, dict) else {}
    try:
        lat = geo.get("schema:latitude")
        lon = geo.get("schema:longitude")
        f_lat = float(lat[0] if isinstance(lat, list) else lat)
        f_lon = float(lon[0] if isinstance(lon, list) else lon)
        return f_lat, f_lon
    except: return None, None

def extract_city(item):

    addr_list = item.get("hasBeenCreatedBy", {}).get("schema:address", [])
    if isinstance(addr_list, list) and len(addr_list) > 0:
        return addr_list[0].get("schema:addressLocality", "Unknown City")
    

    loc_list = item.get("isLocatedAt", [])
    if isinstance(loc_list, list) and len(loc_list) > 0:
        addr = loc_list[0].get("schema:address", [{}])
        if isinstance(addr, list) and len(addr) > 0:
            return addr[0].get("schema:addressLocality", "Unknown City")
            
    return "Unknown City"

#Start_the_process
conn, cur = setup_database()
processed = 0

print("Processing ZIP for Postgres...")
with zipfile.ZipFile(ZIP_FILE) as z:
    for file_name in z.namelist():
        if file_name.startswith("objects/") and file_name.endswith(".json"):
            try:
                with z.open(file_name) as f:
                    data = json.load(TextIOWrapper(f, encoding="utf8"))
                    items = data if isinstance(data, list) else [data]
                    
                    for item in items:
                     
                        label_data = item.get("rdfs:label", {})
                        label = label_data.get("fr", ["Unknown"])[0] if isinstance(label_data, dict) else "Unknown"
                        
                        types = item.get("@type", [])
                        cat_name = [t for t in types if "schema:" not in t][0] if types else "Other"
                        cat_id = get_or_create_category(cur, cat_name)
                        
                        lat, lon = extract_geo(item)
                        city = extract_city(item)
                        rating = item.get("schema:aggregateRating", {}).get("schema:ratingValue")

                      
                        cur.execute("""
                            INSERT INTO pois (label, category_id, city, latitude, longitude, rating, last_update)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (label, cat_id, city, lat, lon, rating, item.get("lastUpdateDatatourisme")))
                        
                        processed += 1
                        if processed % 1000 == 0:
                            conn.commit()
                            print(f"Postgres: {processed} items stored...")
            except:
                continue

conn.commit()
cur.close()
conn.close()
print(f"FINISHED! {processed} items are now in Postgres.")
