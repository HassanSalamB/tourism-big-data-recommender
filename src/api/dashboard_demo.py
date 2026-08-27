"""Curated fallback records for the public Holiday Itinerary portfolio deployment."""

from __future__ import annotations

from typing import Any


PLACES: list[dict[str, Any]] = [
    {"id": "paris-louvre", "name": "Louvre Museum", "city": "Paris", "category": "Museum", "categories": ["Museum", "Art", "Culture"], "lat": 48.8606, "lon": 2.3376, "address": "Rue de Rivoli, Paris", "website": "https://www.louvre.fr"},
    {"id": "paris-jardin", "name": "Jardin du Luxembourg", "city": "Paris", "category": "Garden", "categories": ["Garden", "Outdoors"], "lat": 48.8462, "lon": 2.3372, "address": "75006 Paris", "website": "https://www.senat.fr/visite/jardin"},
    {"id": "paris-orsay", "name": "Musée d'Orsay", "city": "Paris", "category": "Museum", "categories": ["Museum", "Art"], "lat": 48.8600, "lon": 2.3266, "address": "Esplanade Valéry Giscard d'Estaing, Paris", "website": "https://www.musee-orsay.fr"},
    {"id": "paris-montmartre", "name": "Montmartre", "city": "Paris", "category": "District", "categories": ["Culture", "Walking"], "lat": 48.8867, "lon": 2.3431, "address": "Montmartre, Paris", "website": "https://parisjetaime.com"},
    {"id": "ghent-gravensteen", "name": "Gravensteen Castle", "city": "Ghent", "category": "Historic site", "categories": ["History", "Culture"], "lat": 51.0572, "lon": 3.7207, "address": "Sint-Veerleplein 11, Ghent", "website": "https://historischehuizen.stad.gent"},
    {"id": "ghent-stbavo", "name": "Saint Bavo's Cathedral", "city": "Ghent", "category": "Cathedral", "categories": ["History", "Art"], "lat": 51.0536, "lon": 3.7274, "address": "Sint-Baafsplein, Ghent", "website": "https://www.sintbaafskathedraal.be"},
    {"id": "ghent-graslei", "name": "Graslei and Korenlei", "city": "Ghent", "category": "Waterfront", "categories": ["Walking", "Architecture"], "lat": 51.0550, "lon": 3.7203, "address": "Graslei, Ghent", "website": "https://visit.gent.be"},
    {"id": "ghent-stam", "name": "STAM Ghent City Museum", "city": "Ghent", "category": "Museum", "categories": ["Museum", "History"], "lat": 51.0426, "lon": 3.7164, "address": "Godshuizenlaan 2, Ghent", "website": "https://stamgent.be"},
    {"id": "brussels-grandplace", "name": "Grand-Place", "city": "Brussels", "category": "Historic square", "categories": ["History", "Architecture"], "lat": 50.8467, "lon": 4.3525, "address": "Grand-Place, Brussels", "website": "https://www.brussels.be/grand-place"},
    {"id": "brussels-magritte", "name": "Magritte Museum", "city": "Brussels", "category": "Museum", "categories": ["Museum", "Art"], "lat": 50.8424, "lon": 4.3584, "address": "Place Royale 1, Brussels", "website": "https://www.musee-magritte-museum.be"},
    {"id": "brussels-parc", "name": "Parc du Cinquantenaire", "city": "Brussels", "category": "Park", "categories": ["Park", "Outdoors"], "lat": 50.8405, "lon": 4.3928, "address": "Parc du Cinquantenaire, Brussels", "website": "https://visit.brussels"},
    {"id": "brussels-comic", "name": "Belgian Comic Strip Center", "city": "Brussels", "category": "Museum", "categories": ["Museum", "Comics"], "lat": 50.8511, "lon": 4.3600, "address": "Rue des Sables 20, Brussels", "website": "https://www.comicscenter.net"},
]


WEATHER = {
    "Paris": {"temperature_2m": 21.4, "relative_humidity_2m": 58, "rain": 0.0, "wind_speed_10m": 11.2, "observed_at": "Portfolio sample"},
    "Ghent": {"temperature_2m": 18.7, "relative_humidity_2m": 67, "rain": 0.2, "wind_speed_10m": 14.5, "observed_at": "Portfolio sample"},
    "Brussels": {"temperature_2m": 19.2, "relative_humidity_2m": 63, "rain": 0.0, "wind_speed_10m": 12.1, "observed_at": "Portfolio sample"},
}


def demo_summary() -> dict[str, int]:
    categories = {category for place in PLACES for category in place["categories"]}
    return {"places": len(PLACES), "cities": 3, "popular_destinations": 3, "categories": len(categories), "clusters": 6}


def demo_cities() -> list[dict[str, Any]]:
    return [{"city": city, "poi_count": sum(place["city"] == city for place in PLACES)} for city in ("Paris", "Ghent", "Brussels")]


def demo_categories() -> list[str]:
    return sorted({category for place in PLACES for category in place["categories"]})


def demo_places(city: str, categories: list[str] | None = None, limit: int = 50) -> list[dict[str, Any]]:
    selected = [place for place in PLACES if place["city"] == city]
    if categories:
        selected = [place for place in selected if set(place["categories"]) & set(categories)]
    return selected[:limit]


def demo_itinerary(city: str, days: int, max_places: int, categories: list[str] | None = None) -> list[dict[str, Any]]:
    candidates = demo_places(city, categories, limit=200) or demo_places(city, limit=200)
    plans = []
    for day in range(1, days + 1):
        day_places = []
        for position, place in enumerate(candidates[(day - 1) * max_places : day * max_places]):
            start_hour = 9 + position * 2
            day_places.append({**place, "start_time": f"{start_hour:02d}:00", "end_time": f"{start_hour + 1:02d}:30", "recommendations": [item["name"] for item in candidates if item["id"] != place["id"]][:2]})
        plans.append({"day": day, "places": day_places})
    return plans
