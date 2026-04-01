import psycopg2
from psycopg2 import extras
import json
import os
from dotenv import load_dotenv

# 1. Setup Connection (Re-using your env/config logic)
load_dotenv()
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

def run_transformation():
    try:
        conn = psycopg2.connect(
            host="postgres", # or your config['database']['host']
            database="holiday_db",
            user=DB_USER,
            password=DB_PASSWORD,
            port=5432
        )
        cur = conn.cursor()

        # 2. Create the Silver Table (Structured)
        print("🛠️ Creating Silver Layer table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS silver_poi_data (
                id SERIAL PRIMARY KEY,
                name TEXT,
                zip_code TEXT,
                city TEXT,
                category TEXT,
                latitude FLOAT,
                longitude FLOAT,
                transformed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()

        # 3. Read from Bronze (Streaming the database rows)
        # We use a named cursor so Python doesn't load all rows into RAM
        cur_bronze = conn.cursor(name='bronze_steamer')
        cur_bronze.execute("SELECT data_content FROM raw_api_data")

        print("🚀 Transforming Bronze to Silver...")
        
        batch = []
        count = 0

        while True:
            rows = cur_bronze.fetchmany(1000)
            if not rows:
                break

            for (raw_json,) in rows:
                # --- TRANSFORMATION LOGIC ---
                # Safe extraction using .get() to avoid KeyErrors
                name = raw_json.get('rdfs:label', {}).get('en', [None])[0] or raw_json.get('rdfs:label', {}).get('fr', [None])[0]
                
                # Extracting Nested Address
                loc = raw_json.get('isLocatedAt', [{}])[0]
                address = loc.get('schema:address', [{}])[0]
                zip_code = address.get('schema:postalCode')
                city = address.get('schema:addressLocality')
                
                # Extracting Coordinates (Geo)
                geo = loc.get('schema:geo', [{}])[0]
                lat = geo.get('schema:latitude')
                long = geo.get('schema:longitude')
                
                category = raw_json.get('@type', [None])[0]

                batch.append((name, zip_code, city, category, lat, long))

            # 4. Batch Insert into Silver
            extras.execute_values(
                cur,
                "INSERT INTO silver_poi_data (name, zip_code, city, category, latitude, longitude) VALUES %s",
                batch
            )
            conn.commit()
            count += len(batch)
            batch = []
            print(f"✨ Structured {count} records into Silver Layer...")

        print(f"✅ Transformation Complete! {count} records ready for analysis.")
        
        cur_bronze.close()
        cur.close()
        conn.close()

    except Exception as e:
        print(f"❌ Transformation Failed: {e}")

if __name__ == "__main__":
    run_transformation()