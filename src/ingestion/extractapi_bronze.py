from itertools import count
import os
import yaml
import requests
import psycopg2
from psycopg2 import extras
import time
from dotenv import load_dotenv
from pathlib import Path
import json
import ijson
from psycopg2.extras import execute_values 

# 1. Load the "Vault" (Secrets)
load_dotenv()
API_TOKEN = os.getenv("DATATOURISME_TOKEN")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT = os.getenv("DB_PORT")

def load_config():
    """Reads the Control Panel (YAML)"""
    base_dir = Path(__file__).resolve().parent.parent.parent
    config_path = base_dir / "config.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

def should_skip_ingestion(cur):
    cur.execute("SELECT EXISTS (SELECT 1 FROM raw_api_data LIMIT 1);")
    return cur.fetchone()[0] # Returns True if even 1 row exists


def run_ingestion():
    config = load_config()
    
    # Using settings from the YAML
    url = config['api']['feed_url']
    # url + api
    full_url = f"{url}{API_TOKEN}"
    batch_limit = config['database']['batch_size']
    save_path = os.path.join(config['paths']['raw_data_dir'], config['paths']['output_file'])

    # Smart Skip Logic
    if os.path.exists(save_path):
        print(f"📦 Found existing data at {save_path}. Skipping API call.")
    else:
        print(f"📡 Requesting data from {full_url}...")
        # --- STAGE 1: DOWNLOAD (POLLING) ---
        for attempt in range(3):    
            # If your API requires the token, ensure headers are included
            response = requests.get(full_url, stream=True)
            
            if response.status_code == 200:
                print(f"✅ Data ready! Downloading...")
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=1024*1024):
                        f.write(chunk)
                        f.flush() # Forces it to write to disk immediately
                print("💾 Download complete.")
                break
            elif response.status_code == 202:
                print(f"⏳ File is being generated (Attempt {attempt + 1}/3)...")
                time.sleep(10)
            else:
                print(f"⏳ Schedule pending... retrying in 5s (Attempt {attempt + 1}/3)")
                time.sleep(5)
        else:
            print("❌ Download failed.")
            return

    # Database Connection using config + env
    try:
        conn = psycopg2.connect(
            host=config['database']['host'],
            database=config['database']['db_name'],
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
        # creating conn
        cur = conn.cursor()
        
        # 1. Create a "Landing" table (The Data Lake approach)
        # We store the whole JSON object in a 'jsonb' column
        # In your main execution:
        if should_skip_ingestion(cur):
            print("skipped: 🚀 Data Lake already contains data. Skipping ingestion.")
            return
        else:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS raw_api_data (
                id SERIAL PRIMARY KEY,
                data_content JSONB,
                ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
            
        # 2. Stream the data to Postgres (Datalake)
        # If the API returns a list, we loop and insert. and we do that one line at a time so memory dont fail
        # --- THE MEMORY-SAFE DATA LAKE PUSH ---
        print(f"🚀 Starting Streaming Push to Postgres Data Lake...")
        
        try:
            with open(save_path, 'rb') as f:
                # --- PHASE 1: DISCOVERY ---
                print("🔍 Auto-detecting JSON structure...")
                discovery_parser = ijson.parse(f)
                detected_prefix = None
                
                for prefix, event, value in discovery_parser:
                    # We are looking for the first array (start_array)
                    if event == 'start_array':
                        # If the array is inside a key (like @graph), prefix will be 'at-graph'
                        # If it's a flat list at the root, prefix will be empty ''
                        detected_prefix = f"{prefix}.item" if prefix else "item"
                        print(f"✅ Structure Detected! Using prefix: '{detected_prefix}'")
                        break
                
                if not detected_prefix:
                    print("❌ Could not find a valid list in the JSON file.")
                    return

                # --- PHASE 2: STREAMING ---
                # Reset the file to the beginning so we don't miss the first record
                f.seek(0)
                parser = ijson.items(f, detected_prefix)
                
                batch = []
                for count, obj in enumerate(parser):
                    if count == 0:
                        print("🎯 Connection successful. Ingesting data...")
                    
                    batch.append((json.dumps(obj),))
                    
                    if len(batch) >= 1000:
                        extras.execute_values(cur, "INSERT INTO raw_api_data (data_content) VALUES %s", batch)
                        conn.commit()
                        print(f"💾 Landed {count + 1} records...")
                        batch = []

                # Final Flush
                if batch:
                    extras.execute_values(cur, "INSERT INTO raw_api_data (data_content) VALUES %s", batch)
                    conn.commit()
                    print(f"✅ Finished! Total records: {count + 1}")
        
        except Exception as e:
            print(f"❌ Error during streaming push: {e}")
            return


        cur.close()
        conn.close()
        print("🔒 Connection closed successfully. Goodbye!")
        
    except Exception as e:
        print(f"❌ Error during Database Push: {e}")


if __name__ == "__main__":
    run_ingestion()
    
    
