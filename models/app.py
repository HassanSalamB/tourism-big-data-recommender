import os
import sys
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sklearn.cluster import KMeans
from typing import List, Optional
from datetime import datetime, timedelta

# 1. Setup paths for utils access
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

try:
    from utils.connections import conn_env, neo4j_env
except ImportError:
    raise RuntimeError("❌ Connection modules not found in utils folder.")

app = FastAPI(title="Tourism Itinerary API")

# 2. Pydantic data models
class PlannedPlace(BaseModel):
    name: str
    category: str
    rating: Optional[float] = None
    start_time: str
    end_time: str
    recommendations: List[str]

class DayPlan(BaseModel):
    day: int
    places: List[PlannedPlace]

class ItineraryRequest(BaseModel):
    city: str
    days: int = 3
    max_places_per_day: int = 5

# 3. Fetch recommendations from Neo4j graph database
def get_graph_recommendations(poi_label, city):
    try:
        conf = neo4j_env()
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(conf['uri'], auth=conf['auth'])
        with driver.session() as session:
            query = """
            MATCH (p:POI {label: $label, city: $city})-->(c:Category)<--(similar:POI)
            WHERE similar.label <> $label
            RETURN similar.label AS rec LIMIT 3
            """
            result = session.run(query, label=poi_label, city=city)
            return [record["rec"] for record in result]
    except Exception:
        return [] # Return empty list if graph DB is unavailable
    finally:
        if 'driver' in locals(): driver.close()

@app.post("/generate-itinerary", response_model=List[DayPlan])
def generate_itinerary(request: ItineraryRequest):
    conn = None
    try:
        conn = conn_env()
        
        # 4. Optimized query using JOIN to fetch real category names
        query = """
            SELECT p.label, p.latitude, p.longitude, p.rating, 
                   COALESCE(c.name, 'Tourism') as category_name
            FROM pois p
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE LOWER(p.city) = LOWER(%s)
        """
        df = pd.read_sql(query, conn, params=[request.city])
        
        if df.empty:
            raise HTTPException(status_code=404, detail=f"City '{request.city}' not found.")

        # 5. Clustering logic (K-Means) to distribute places across days
        num_clusters = min(request.days, len(df))
        coords = df[['latitude', 'longitude']].values
        kmeans = KMeans(n_clusters=num_clusters, random_state=42, n_init='auto').fit(coords)
        df['day_assignment'] = kmeans.labels_

        itinerary = []
        for d in range(num_clusters):
            day_data = df[df['day_assignment'] == d].head(request.max_places_per_day)
            
            # Scheduling starts at 09:00 AM
            current_time = datetime.strptime("09:00", "%H:%M")
            planned_places = []
            
            for _, row in day_data.iterrows():
                # Get smart recommendations for each POI
                recs = get_graph_recommendations(row['label'], request.city)
                
                visit_duration = timedelta(hours=2)
                end_time = current_time + visit_duration
                
                planned_places.append(PlannedPlace(
                    name=row['label'],
                    category=row['category_name'],
                    rating=row['rating'],
                    start_time=current_time.strftime("%H:%M"),
                    end_time=end_time.strftime("%H:%M"),
                    recommendations=recs
                ))
                
                # 30-minute gap between locations
                current_time = end_time + timedelta(minutes=30)

            itinerary.append(DayPlan(day=d + 1, places=planned_places))
            
        return itinerary

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Ensure database connection is always closed
        if conn:
            conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
