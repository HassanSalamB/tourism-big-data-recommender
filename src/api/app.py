"""FastAPI service for exploring generated holiday itinerary data."""

from __future__ import annotations

import os
import sys
from contextlib import closing
from datetime import datetime, timedelta
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sklearn.cluster import KMeans

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(CURRENT_DIR)
PROJECT_ROOT = os.path.dirname(SRC_DIR)
for path in (PROJECT_ROOT, SRC_DIR):
    if path not in sys.path:
        sys.path.append(path)

try:
    from src.utils.connections import conn_env, neo4j_env
except ImportError:
    from utils.connections import conn_env, neo4j_env


app = FastAPI(title="Holiday Itinerary API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ItineraryRequest(BaseModel):
    city: str = Field(..., min_length=1)
    days: int = Field(default=3, ge=1, le=14)
    max_places_per_day: int = Field(default=5, ge=1, le=12)
    categories: list[str] = Field(default_factory=list)


class PlannedPlace(BaseModel):
    id: str
    name: str
    city: str | None = None
    category: str = "Tourism"
    categories: list[str] = Field(default_factory=list)
    lat: float
    lon: float
    address: str | None = None
    description: str | None = None
    website: str | None = None
    start_time: str
    end_time: str
    recommendations: list[str] = Field(default_factory=list)


class DayPlan(BaseModel):
    day: int
    places: list[PlannedPlace]


class CitySummary(BaseModel):
    city: str
    poi_count: int


class AppSummary(BaseModel):
    places: int
    cities: int
    categories: int
    clusters: int


def _query_dataframe(conn, query: str, params: tuple[Any, ...] = ()) -> pd.DataFrame:
    with conn.cursor() as cursor:
        cursor.execute(query, params)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
    return pd.DataFrame(rows, columns=columns)


def _json_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df.empty:
        return []
    # Pandas represents missing values as NaN/NaT, but strict JSON does not allow
    # NaN floats. Convert every dataframe missing value to Python None.
    clean_df = df.astype(object).where(pd.notna(df), None)
    return clean_df.to_dict(orient="records")


def _json_value(value):
    return None if pd.isna(value) else value


def _database_ready(conn) -> bool:
    with conn.cursor() as cursor:
        cursor.execute("SELECT to_regclass('public.silver_places')")
        return cursor.fetchone()[0] is not None


def _places_query(where_clause: str = "", limit_clause: str = ""):
    return f"""
        WITH filtered_places AS (
            SELECT
                p.id,
                p.name,
                p.city,
                p.lat,
                p.lon,
                p.address,
                p.description,
                p.website
            FROM silver_places p
            {where_clause}
            ORDER BY p.name
            {limit_clause}
        )
        SELECT
            p.id,
            p.name,
            p.city,
            p.lat,
            p.lon,
            p.address,
            p.description,
            p.website,
            COALESCE(
                ARRAY_AGG(DISTINCT c.name) FILTER (WHERE c.name IS NOT NULL),
                ARRAY[]::TEXT[]
            ) AS categories
        FROM filtered_places p
        LEFT JOIN silver_place_categories pc ON p.id = pc.place_id
        LEFT JOIN silver_categories c ON pc.category_id = c.id
        GROUP BY p.id, p.name, p.city, p.lat, p.lon, p.address, p.description, p.website
        ORDER BY p.name
    """


def _load_places_for_city(conn, city: str, limit: int) -> pd.DataFrame:
    query = _places_query(
        where_clause="WHERE LOWER(p.city) = LOWER(%s)",
        limit_clause="LIMIT %s",
    )
    return _query_dataframe(conn, query, (city, limit))


def _get_recommendations_for_places(
    place_ids: list[str], city: str | None, limit: int = 3
) -> dict[str, list[str]]:
    if not place_ids:
        return {}
    try:
        from neo4j import GraphDatabase, Query

        uri, auth = neo4j_env()
        driver = GraphDatabase.driver(uri, auth=auth, connection_timeout=2)
        try:
            with driver.session() as session:
                result = session.run(
                    Query(
                        """
                    UNWIND $place_ids AS place_id
                    MATCH (p:POI {id: place_id})-[:HAS_CATEGORY]->(:Category)<-[:HAS_CATEGORY]-(similar:POI)
                    OPTIONAL MATCH (similar)-[:LOCATED_IN]->(city:City)
                    WHERE similar.id <> place_id
                      AND ($city IS NULL OR toLower(city.name) = toLower($city))
                      AND similar.label IS NOT NULL
                    WITH place_id, similar.label AS name
                    ORDER BY name
                    WITH place_id, collect(DISTINCT name)[0..$limit] AS recommendations
                    RETURN place_id, recommendations
                    """,
                        timeout=3,
                    ),
                    place_ids=place_ids,
                    city=city,
                    limit=limit,
                )
                return {
                    record["place_id"]: list(record["recommendations"] or [])
                    for record in result
                }
        finally:
            driver.close()
    except Exception:
        return {}


def _row_categories(row) -> list[str]:
    categories = row.get("categories") or []
    return list(categories) if isinstance(categories, (list, tuple)) else []


def _normalize_categories(categories: list[str] | None) -> list[str]:
    if not categories:
        return []
    normalized = []
    seen = set()
    for category in categories:
        cleaned = category.strip()
        key = cleaned.lower()
        if not cleaned or key in seen:
            continue
        normalized.append(cleaned)
        seen.add(key)
    return normalized


def _category_match_count(
    row_categories: list[str], preferred_categories: list[str]
) -> int:
    preferred = {category.lower() for category in preferred_categories}
    return sum(1 for category in row_categories if category.lower() in preferred)


def _select_day_rows(
    day_rows: pd.DataFrame, preferred_categories: list[str], max_places: int
) -> list[dict[str, Any]]:
    sorted_rows = day_rows.sort_values(["distance_to_day_center", "name"])
    if not preferred_categories:
        return sorted_rows.head(max_places).to_dict(orient="records")

    interest_slots = min(
        len(preferred_categories),
        max(1, max_places // 2),
        max_places,
    )
    preferred_rows = sorted_rows[sorted_rows["category_match_count"] > 0].head(
        interest_slots
    )
    filler_rows = sorted_rows[~sorted_rows["id"].isin(preferred_rows["id"])].head(
        max_places - len(preferred_rows)
    )
    return pd.concat([preferred_rows, filler_rows]).to_dict(orient="records")


@app.get("/health")
def health():
    with closing(conn_env()) as conn:
        return {"status": "ok", "database_ready": _database_ready(conn)}


@app.get("/summary", response_model=AppSummary)
def summary():
    with closing(conn_env()) as conn:
        if not _database_ready(conn):
            raise HTTPException(
                status_code=503, detail="silver_places is not loaded yet."
            )
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    (SELECT COUNT(*) FROM silver_places) AS places,
                    (SELECT COUNT(DISTINCT city) FROM silver_places WHERE city IS NOT NULL) AS cities,
                    (SELECT COUNT(*) FROM silver_categories) AS categories
                """)
            places, cities, categories = cursor.fetchone()
            cursor.execute("SELECT to_regclass('public.gold_clusters')")
            if cursor.fetchone()[0] is None:
                clusters = 0
            else:
                cursor.execute("SELECT COUNT(*) FROM gold_clusters")
                clusters = cursor.fetchone()[0]
    return AppSummary(
        places=places,
        cities=cities,
        categories=categories,
        clusters=clusters,
    )


@app.get("/cities", response_model=list[CitySummary])
def cities(limit: int = Query(default=25, ge=1, le=200)):
    with closing(conn_env()) as conn:
        if not _database_ready(conn):
            raise HTTPException(
                status_code=503, detail="silver_places is not loaded yet."
            )
        df = _query_dataframe(
            conn,
            """
            SELECT city, COUNT(*) AS poi_count
            FROM silver_places
            WHERE city IS NOT NULL AND city <> ''
            GROUP BY city
            ORDER BY poi_count DESC, city
            LIMIT %s
            """,
            (limit,),
        )
    return [
        CitySummary(city=row.city, poi_count=row.poi_count) for row in df.itertuples()
    ]


@app.get("/categories", response_model=list[str])
def categories(limit: int = Query(default=100, ge=1, le=500)):
    with closing(conn_env()) as conn:
        if not _database_ready(conn):
            raise HTTPException(
                status_code=503, detail="silver_places is not loaded yet."
            )
        df = _query_dataframe(
            conn,
            "SELECT name FROM silver_categories ORDER BY name LIMIT %s",
            (limit,),
        )
    return df["name"].tolist()


@app.get("/places")
def places(
    city: str | None = None,
    category: str | None = None,
    categories: list[str] | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
):
    filters = []
    params: list[Any] = []
    if city:
        filters.append("LOWER(p.city) = LOWER(%s)")
        params.append(city)
    selected_categories = _normalize_categories([category] if category else categories)
    if selected_categories:
        filters.append("""
            EXISTS (
                SELECT 1
                FROM silver_place_categories pc_filter
                JOIN silver_categories c_filter ON pc_filter.category_id = c_filter.id
                WHERE pc_filter.place_id = p.id
                  AND LOWER(c_filter.name) = ANY(%s)
            )
            """)
        params.append([category.lower() for category in selected_categories])

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    params.append(limit)
    with closing(conn_env()) as conn:
        if not _database_ready(conn):
            raise HTTPException(
                status_code=503, detail="silver_places is not loaded yet."
            )
        df = _query_dataframe(
            conn,
            _places_query(
                where_clause=where_clause,
                limit_clause="LIMIT %s",
            ),
            tuple(params),
        )
    return _json_records(df)


@app.post("/generate-itinerary", response_model=list[DayPlan])
def generate_itinerary(request: ItineraryRequest):
    preferred_categories = _normalize_categories(request.categories)
    with closing(conn_env()) as conn:
        if not _database_ready(conn):
            raise HTTPException(
                status_code=503, detail="silver_places is not loaded yet."
            )
        df = _load_places_for_city(
            conn,
            request.city.strip(),
            min(max(request.days * request.max_places_per_day * 50, 500), 2000),
        )

    if df.empty:
        raise HTTPException(
            status_code=404, detail=f"City '{request.city}' was not found."
        )

    cluster_count = min(request.days, len(df))
    if cluster_count > 1:
        coords = df[["lat", "lon"]].astype(float).values
        kmeans = KMeans(
            n_clusters=cluster_count,
            random_state=42,
            n_init=10,
        )
        df["day_assignment"] = kmeans.fit_predict(coords)
        df["distance_to_day_center"] = [
            ((lat - kmeans.cluster_centers_[label][0]) ** 2)
            + ((lon - kmeans.cluster_centers_[label][1]) ** 2)
            for (lat, lon), label in zip(coords, df["day_assignment"])
        ]
    else:
        df["day_assignment"] = 0
        df["distance_to_day_center"] = 0
    df["category_match_count"] = df["categories"].map(
        lambda categories: _category_match_count(
            list(categories or []), preferred_categories
        )
    )

    selected_rows_by_day = []
    for day_index in range(cluster_count):
        selected_rows_by_day.append(
            (
                day_index,
                _select_day_rows(
                    df[df["day_assignment"] == day_index],
                    preferred_categories,
                    request.max_places_per_day,
                ),
            )
        )

    selected_place_ids = [
        row["id"] for _, rows in selected_rows_by_day for row in rows if row.get("id")
    ]
    recommendation_map = _get_recommendations_for_places(
        selected_place_ids, request.city.strip()
    )

    itinerary: list[DayPlan] = []
    for day_index, rows in selected_rows_by_day:
        current_time = datetime.strptime("09:00", "%H:%M")
        planned_places = []

        for row in rows:
            end_time = current_time + timedelta(hours=2)
            categories = _row_categories(row)
            planned_places.append(
                PlannedPlace(
                    id=row["id"],
                    name=row["name"],
                    city=row.get("city"),
                    category=categories[0] if categories else "Tourism",
                    categories=categories,
                    lat=row["lat"],
                    lon=row["lon"],
                    address=_json_value(row.get("address")),
                    description=_json_value(row.get("description")),
                    website=_json_value(row.get("website")),
                    start_time=current_time.strftime("%H:%M"),
                    end_time=end_time.strftime("%H:%M"),
                    recommendations=recommendation_map.get(row["id"], []),
                )
            )
            current_time = end_time + timedelta(minutes=30)

        itinerary.append(DayPlan(day=day_index + 1, places=planned_places))

    return itinerary


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
