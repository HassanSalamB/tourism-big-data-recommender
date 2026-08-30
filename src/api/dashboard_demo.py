"""Curated fallback records for the public Holiday Itinerary deployment."""

from __future__ import annotations

from typing import Any


def _place(
    slug: str,
    name: str,
    category: str,
    categories: list[str],
    lat: float,
    lon: float,
    address: str,
    website: str,
) -> dict[str, Any]:
    return {
        "id": f"paris-{slug}", "name": name, "city": "Paris", "category": category,
        "categories": categories, "lat": lat, "lon": lon, "address": address, "website": website,
    }


# Ordered loosely by neighbourhood so selections form useful day routes.
PLACES: list[dict[str, Any]] = [
    _place("louvre", "Louvre Museum", "Museum", ["Museum", "Art", "Culture", "History"], 48.8606, 2.3376, "Rue de Rivoli, Paris", "https://www.louvre.fr"),
    _place("tuileries", "Tuileries Garden", "Garden", ["Garden", "Outdoors", "Walking", "Family"], 48.8635, 2.3275, "Place de la Concorde, Paris", "https://parisjetaime.com"),
    _place("orangerie", "Musée de l'Orangerie", "Museum", ["Museum", "Art", "Culture"], 48.8638, 2.3227, "Jardin des Tuileries, Paris", "https://www.musee-orangerie.fr"),
    _place("orsay", "Musée d'Orsay", "Museum", ["Museum", "Art", "Culture", "History"], 48.8600, 2.3266, "Esplanade Valéry Giscard d'Estaing, Paris", "https://www.musee-orsay.fr"),
    _place("palais-royal", "Palais-Royal Garden", "Garden", ["Garden", "Architecture", "Walking", "History"], 48.8647, 2.3376, "Galerie de Montpensier, Paris", "https://parisjetaime.com"),
    _place("place-vendome", "Place Vendôme", "Square", ["Architecture", "History", "Walking", "Shopping"], 48.8675, 2.3294, "Place Vendôme, Paris", "https://parisjetaime.com"),
    _place("notre-dame", "Notre-Dame Cathedral", "Landmark", ["Architecture", "Culture", "History", "Walking"], 48.8530, 2.3499, "6 Parvis Notre-Dame, Paris", "https://www.notredamedeparis.fr"),
    _place("sainte-chapelle", "Sainte-Chapelle", "Monument", ["Architecture", "Art", "Culture", "History"], 48.8554, 2.3450, "10 Boulevard du Palais, Paris", "https://www.sainte-chapelle.fr"),
    _place("conciergerie", "Conciergerie", "Monument", ["Architecture", "Culture", "History"], 48.8559, 2.3452, "2 Boulevard du Palais, Paris", "https://www.paris-conciergerie.fr"),
    _place("latin-quarter", "Latin Quarter", "District", ["Culture", "History", "Walking", "Food"], 48.8494, 2.3430, "Latin Quarter, Paris", "https://parisjetaime.com"),
    _place("pantheon", "Panthéon", "Monument", ["Architecture", "Culture", "History"], 48.8462, 2.3460, "Place du Panthéon, Paris", "https://www.paris-pantheon.fr"),
    _place("luxembourg", "Jardin du Luxembourg", "Garden", ["Garden", "Outdoors", "Walking", "Family"], 48.8462, 2.3372, "75006 Paris", "https://www.senat.fr/visite/jardin"),
    _place("cluny", "Musée de Cluny", "Museum", ["Museum", "Art", "Culture", "History"], 48.8506, 2.3431, "28 Rue du Sommerard, Paris", "https://www.musee-moyenage.fr"),
    _place("marais", "Le Marais", "District", ["Culture", "History", "Walking", "Food", "Shopping"], 48.8576, 2.3622, "Le Marais, Paris", "https://parisjetaime.com"),
    _place("place-vosges", "Place des Vosges", "Square", ["Architecture", "Garden", "History", "Walking"], 48.8556, 2.3655, "Place des Vosges, Paris", "https://parisjetaime.com"),
    _place("picasso", "Musée Picasso Paris", "Museum", ["Museum", "Art", "Culture"], 48.8599, 2.3623, "5 Rue de Thorigny, Paris", "https://www.museepicassoparis.fr"),
    _place("pompidou", "Centre Pompidou", "Museum", ["Museum", "Art", "Architecture", "Culture", "Family"], 48.8606, 2.3522, "Place Georges-Pompidou, Paris", "https://www.centrepompidou.fr"),
    _place("canal-saint-martin", "Canal Saint-Martin", "Waterfront", ["Outdoors", "Walking", "Food"], 48.8714, 2.3655, "Quai de Valmy, Paris", "https://parisjetaime.com"),
    _place("montmartre", "Montmartre", "District", ["Culture", "History", "Walking", "Food", "Views"], 48.8867, 2.3431, "Montmartre, Paris", "https://parisjetaime.com"),
    _place("sacre-coeur", "Sacré-Cœur Basilica", "Landmark", ["Architecture", "Culture", "History", "Views"], 48.8867, 2.3431, "35 Rue du Chevalier de la Barre, Paris", "https://www.sacre-coeur-montmartre.com"),
    _place("musee-montmartre", "Musée de Montmartre", "Museum", ["Museum", "Art", "Culture", "History"], 48.8879, 2.3407, "12 Rue Cortot, Paris", "https://museedemontmartre.fr"),
    _place("moulin-rouge", "Moulin Rouge", "Landmark", ["Culture", "History", "Nightlife"], 48.8841, 2.3322, "82 Boulevard de Clichy, Paris", "https://www.moulinrouge.fr"),
    _place("arc-triomphe", "Arc de Triomphe", "Monument", ["Architecture", "History", "Views", "Walking"], 48.8738, 2.2950, "Place Charles de Gaulle, Paris", "https://www.paris-arc-de-triomphe.fr"),
    _place("champs-elysees", "Champs-Élysées", "Avenue", ["Walking", "Shopping", "Architecture"], 48.8698, 2.3076, "Avenue des Champs-Élysées, Paris", "https://parisjetaime.com"),
    _place("eiffel", "Eiffel Tower", "Landmark", ["Architecture", "History", "Family", "Views"], 48.8584, 2.2945, "5 Avenue Anatole France, Paris", "https://www.toureiffel.paris"),
    _place("champ-mars", "Champ de Mars", "Park", ["Garden", "Outdoors", "Walking", "Family", "Views"], 48.8556, 2.2986, "2 Allée Adrienne Lecouvreur, Paris", "https://parisjetaime.com"),
    _place("trocadero", "Trocadéro Gardens", "Garden", ["Garden", "Outdoors", "Walking", "Family", "Views"], 48.8629, 2.2870, "Place du Trocadéro, Paris", "https://parisjetaime.com"),
    _place("rodin", "Musée Rodin", "Museum", ["Museum", "Art", "Garden", "Culture"], 48.8553, 2.3158, "77 Rue de Varenne, Paris", "https://www.musee-rodin.fr"),
    _place("invalides", "Hôtel des Invalides", "Monument", ["Museum", "Architecture", "History", "Culture"], 48.8566, 2.3126, "129 Rue de Grenelle, Paris", "https://www.musee-armee.fr"),
    _place("seine", "Seine River Walk", "Waterfront", ["Outdoors", "Walking", "Family", "Views"], 48.8580, 2.3160, "Berges de Seine, Paris", "https://parisjetaime.com"),
]


WEATHER = {
    "Paris": {"temperature_2m": 21.4, "relative_humidity_2m": 58, "rain": 0.0, "wind_speed_10m": 11.2, "observed_at": "Portfolio sample"},
}


def demo_summary() -> dict[str, int]:
    categories = {category for place in PLACES for category in place["categories"]}
    cities = {place["city"] for place in PLACES}
    return {"places": len(PLACES), "cities": len(cities), "popular_destinations": len(cities), "categories": len(categories), "clusters": 6}


def demo_cities() -> list[dict[str, Any]]:
    cities = sorted({place["city"] for place in PLACES})
    return [{"city": city, "poi_count": sum(place["city"] == city for place in PLACES)} for city in cities]


def demo_categories() -> list[str]:
    return sorted({category for place in PLACES for category in place["categories"]})


def demo_places(city: str, categories: list[str] | None = None, limit: int = 50) -> list[dict[str, Any]]:
    selected = [place for place in PLACES if place["city"] == city]
    if categories:
        selected = [place for place in selected if set(place["categories"]) & set(categories)]
    return selected[:limit]


def demo_itinerary(city: str, days: int, max_places: int, categories: list[str] | None = None) -> list[dict[str, Any]]:
    candidates = demo_places(city, categories, limit=200)
    if not candidates:
        candidates = demo_places(city, limit=200)

    # Fill every requested day before adding second and later stops.
    selected = candidates[: days * max_places]
    day_buckets: list[list[dict[str, Any]]] = [[] for _ in range(days)]
    for index, place in enumerate(selected):
        day_buckets[index % days].append(place)

    plans = []
    for day, bucket in enumerate(day_buckets, start=1):
        day_places = []
        for position, place in enumerate(bucket):
            start_hour = 9 + position * 2
            related = [item["name"] for item in candidates if item["id"] != place["id"]][:2]
            day_places.append({
                **place,
                "start_time": f"{start_hour:02d}:00",
                "end_time": f"{start_hour + 1:02d}:30",
                "recommendations": related,
            })
        plans.append({"day": day, "places": day_places})
    return plans
