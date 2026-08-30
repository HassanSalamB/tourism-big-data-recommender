import unittest

from src.api.map_view import build_leaflet_map


class MapViewTests(unittest.TestCase):
    def test_map_uses_leaflet_and_contains_every_place(self) -> None:
        places = [
            {"name": "First", "lat": 48.86, "lon": 2.33, "address": "Paris", "categories": ["Art"]},
            {"name": "Second", "lat": 48.87, "lon": 2.34, "address": "Paris", "categories": ["Garden"]},
        ]

        route_map = build_leaflet_map(places)
        rendered = route_map.get_root().render() if route_map is not None else ""

        self.assertIn("leaflet", rendered.lower())
        self.assertIn("tile.openstreetmap.org", rendered)
        self.assertIn("First", rendered)
        self.assertIn("Second", rendered)
        self.assertNotIn("cartodb", rendered.lower())
        self.assertNotIn("deck.gl", rendered.lower())

    def test_map_rejects_places_without_coordinates(self) -> None:
        self.assertIsNone(build_leaflet_map([{"name": "Unknown"}]))


if __name__ == "__main__":
    unittest.main()
