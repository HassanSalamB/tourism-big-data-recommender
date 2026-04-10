import zipfile
import json
from io import TextIOWrapper
from neo4j import GraphDatabase

# ---setting---
ZIP_FILE = "flux-25818-202603141313.zip"
URI = "bolt://localhost:7687"
AUTH = ("neo4j", "neo4j") 
class Neo4jImporter:
    def __init__(self, uri, auth):
        self.driver = GraphDatabase.driver(uri, auth=auth)

    def close(self):
        self.driver.close()

    def clear_database(self):
     
        with self.driver.session() as session:
            print("Cleaning database...")
            session.run("MATCH (n) DETACH DELETE n")
          
            try:
                session.run("CREATE CONSTRAINT ON (c:Category) ASSERT c.name IS UNIQUE")
                session.run("CREATE CONSTRAINT ON (city:City) ASSERT city.name IS UNIQUE")
            except:
                print("Constraints already exist or skipped.")

    def import_batch(self, batch):
       
        with self.driver.session() as session:
            query = """
            UNWIND $batch as item
            MERGE (c:Category {name: item.category})
            MERGE (city:City {name: item.city})
            CREATE (p:POI {
                label: item.label,
                last_update: item.last_update,
                latitude: item.latitude,
                longitude: item.longitude,
                rating: item.rating
            })
            CREATE (p)-[:HAS_CATEGORY]->(c)
            CREATE (p)-[:LOCATED_IN]->(city)
            """
            session.run(query, batch=batch)

#----Function_for_Exracting_data-----

def extract_label(item):
  
    label_data = item.get("rdfs:label", {})
    if isinstance(label_data, dict):
        return label_data.get("fr", ["Unknown"])[0]
    return item.get("label", "Unknown POI")

def extract_category(item):
  
    types = item.get("@type", [])
    if isinstance(types, list):

        clean_types = [t for t in types if "schema:" not in t]
        return clean_types[0] if clean_types else types[0]
    return "PointOfInterest"

def extract_geo(item):

    loc_list = item.get("isLocatedAt", [])
    if isinstance(loc_list, list) and len(loc_list) > 0:
        loc = loc_list[0]
    else:
        loc = item.get("isLocatedAt", {})
    
    geo = loc.get("schema:geo", {}) if isinstance(loc, dict) else {}
    lat = geo.get("schema:latitude")
    lon = geo.get("schema:longitude")
    
    try:
     
        f_lat = float(lat[0] if isinstance(lat, list) else lat)
        f_lon = float(lon[0] if isinstance(lon, list) else lon)
        return f_lat, f_lon
    except:
        return None, None

def extract_city(item):
   
    address_list = item.get("hasBeenCreatedBy", {}).get("schema:address", [])
    if isinstance(address_list, list) and len(address_list) > 0:
        return address_list[0].get("schema:addressLocality", "Unknown City")
    return "Unknown City"


#----Creat_database-----
importer = Neo4jImporter(URI, AUTH)
importer.clear_database()

processed = 0
batch_data = []

print("Reading files from ZIP objects folder...")
with zipfile.ZipFile(ZIP_FILE) as z:
    for file_name in z.namelist():
     
        if file_name.startswith("objects/") and file_name.endswith(".json"):
            try:
                with z.open(file_name) as f:
                    data = json.load(TextIOWrapper(f, encoding="utf8"))
                    items = data if isinstance(data, list) else [data]
                    
                    for item in items:
                        lat, lon = extract_geo(item)
                        
                        poi_entry = {
                            "label": extract_label(item),
                            "category": extract_category(item),
                            "city": extract_city(item),
                            "last_update": item.get("lastUpdateDatatourisme"),
                            "latitude": lat,
                            "longitude": lon,
                            "rating": item.get("schema:aggregateRating", {}).get("schema:ratingValue")
                        }
                        
                        batch_data.append(poi_entry)
                        processed += 1

                     
                        if len(batch_data) >= 500:
                            importer.import_batch(batch_data)
                            batch_data = []
                            print(f"Total processed: {processed}")
            except:
                continue


if batch_data:
    importer.import_batch(batch_data)

print(f"\nFinished! Total {processed} POIs stored in Neo4j.")
importer.close()
