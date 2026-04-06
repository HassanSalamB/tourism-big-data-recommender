import json
import os
import time
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values
import requests
import yaml
import ijson

# =============================================================================
# 1. LOAD ENVIRONMENT
# =============================================================================
load_dotenv()

API_TOKEN = os.getenv("DATATOURISME_TOKEN")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_NAME = os.getenv("DB_NAME")
DB_HOST = os.getenv("DB_HOST")


# =============================================================================
# 2. CONFIG
# =============================================================================
def load_config():
    """Loads YAML config from parent directory."""
    base_dir = Path(__file__).resolve().parent.parent.parent
    config_path = base_dir / "config.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


config = load_config()


# =============================================================================
# 3. INGESTION LOGIC
# =============================================================================
def check_and_create_table(cur):
    """Ensure the table exists first, then check for existing data."""
    # 1. Create table first (No UNIQUE constraint on JSONB to avoid index size errors)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS raw_api_data (
            id SERIAL PRIMARY KEY,
            data_content JSONB,
            ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    # 2. Now check if it's empty
    cur.execute("SELECT EXISTS (SELECT 1 FROM raw_api_data LIMIT 1);")
    if cur.fetchone()[0]:
        print("✅ Table already contains data. Proceeding with append...")
    else:
        print("✅ Table is empty. Starting fresh ingestion...")


def download_data(url, save_path):
    """Download and save API data to file."""
    full_url = f"{url}{API_TOKEN}" if API_TOKEN else url

    if os.path.exists(save_path):
        print(f"✅ File exists: {save_path}")
        return True

    print(f"📡 Requesting data from {full_url}...")

    # Retry logic for 202 status codes
    headers = {"Accept": "application/zip, application/octet-stream"}
    for attempt in range(3):
        response = requests.get(full_url, headers=headers, stream=True)
        if response.status_code == 200:
            print("✅ Data ready! Downloading...")
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    f.write(chunk)
                    f.flush()
            print("💾 Download complete.")
            return True
        elif response.status_code == 202:
            print(f"⏳ Waiting for file (Attempt {attempt + 1}/3)...")
            time.sleep(10)
        elif response.status_code != 200:
            print(f"❌ Download failed: {response.status_code}")
            return False
    return False


def auto_detect_prefix(f):
    """
    Auto-detects the JSON array prefix by searching for the first 'start_array' event.
    Optimized for large files and JSON-LD (@graph) structures.
    """
    print("🔍 Auto-detecting JSON structure...")

    # Reset file pointer to ensure we start from the beginning
    f.seek(0)

    # ijson.parse returns (prefix, event, value)
    discovery_parser = ijson.parse(f)
    detected_prefix = None

    try:
        for prefix, event, value in discovery_parser:
            # We are looking for the first array (start_array)
            if event == "start_array":
                # If the array is inside a key (like @graph), prefix will be '@graph'
                # If it's a flat list at the root, prefix will be empty ''

                # Logic: If prefix exists, we use prefix.item. If not, just item.
                detected_prefix = f"{prefix}.item" if prefix else "item"
                print(f"✅ Structure Detected! Using prefix: '{detected_prefix}'")
                break

    except Exception as e:
        print(f"❌ Error during structural discovery: {e}")
        return None

    if not detected_prefix:
        print("⚠️ Could not find a valid list/array in the JSON file.")
        # Optional: You could add a manual fallback here if you know the key
        # return "@graph.item"

    # Reset file pointer again so the calling function can start streaming immediately
    f.seek(0)
    return detected_prefix


def ingest_data(conn, cur, f, prefix):
    """Stream data from file into Postgres in batches."""
    batch = []
    total_count = 0

    # Ensure we are at the start of the file after prefix detection
    f.seek(0)

    try:
        # ijson.items yields individual dictionaries from the array
        parser = ijson.items(f, prefix)

        for count, obj in enumerate(parser):
            if count == 0:
                print("🎯 Connection successful. Starting data ingestion...")

            try:
                # Convert the dict to a JSON string for the DB
                data = json.dumps(obj)
                batch.append((data,))
                total_count = count + 1

                # Batch Insert
                if len(batch) >= 1000:
                    execute_values(
                        cur, "INSERT INTO raw_api_data (data_content) VALUES %s", batch
                    )
                    conn.commit()
                    print(f"💾 Landed {total_count} records...")
                    batch = []

            except Exception as e:
                print(f"❌ Error processing record {count}: {e}")

            # Helpful progress for a 4GB file
            if total_count % 5000 == 0:
                print(f"🚀 Progress: {total_count} records processed so far...")

        # Final Flush for the remainder
        if batch:
            execute_values(
                cur, "INSERT INTO raw_api_data (data_content) VALUES %s", batch
            )
            conn.commit()
            print(f"✅ Finished! Total records ingested: {total_count}")

    except Exception as e:
        print(f"🛑 Critical error during streaming: {e}")
        conn.rollback()  # Rollback if the stream breaks


# =============================================================================
# 4. MAIN EXECUTION
# =============================================================================
def run_ingestion():
    """Runs the full ingestion pipeline using safe context managers."""
    print("🚀 Initializing ingestion process...")

    # 1. Establish Connection
    try:
        with psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
        ) as conn:

            # 2. Open Cursor
            with conn.cursor() as cur:
                print("✅ Connected to database")
                check_and_create_table(cur)

                # 3. Handle File Download
                save_path = os.path.join(
                    config["paths"]["raw_data_dir"], config["paths"]["output_file"]
                )

                if not download_data(config["api"]["feed_url"], save_path):
                    print("❌ Download failed. Exiting.")
                    return

                # 4. Process File (Open ONCE)
                print("🔍 Detecting JSON structure...")
                with open(save_path, "rb") as f:
                    # Step A: Find the array path (@graph.item or item)
                    prefix = auto_detect_prefix(f)

                    if not prefix:
                        print("❌ Could not detect JSON structure. Exiting.")
                        return

                    print(f"🎯 Detected prefix: {prefix}")

                    # Step B: Reset the file pointer to the beginning
                    f.seek(0)

                    # Step C: Stream the data into Postgres
                    ingest_data(conn, cur, f, prefix)

            # Cursor automatically closes here
            print("🧹 Cursor closed.")

    except Exception as e:
        print(f"🛑 Error during ingestion: {e}")
    # Connection automatically closes here via the 'with' block
    print("🏁 Ingestion run complete.")


# =============================================================================
# ENTRY POINT
# =============================================================================
if __name__ == "__main__":
    run_ingestion()
