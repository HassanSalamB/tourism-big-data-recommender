import unittest

from src.api.dashboard_demo import PLACES, WEATHER, demo_cities, demo_itinerary, demo_summary


class DashboardDemoTests(unittest.TestCase):
    def test_demo_uses_only_declared_france_sample(self) -> None:
        cities = {place["city"] for place in PLACES}

        self.assertEqual(cities, {"Paris"})
        self.assertEqual(set(WEATHER), cities)
        self.assertEqual([item["city"] for item in demo_cities()], ["Paris"])

    def test_summary_is_derived_from_demo_records(self) -> None:
        summary = demo_summary()

        self.assertEqual(summary["places"], len(PLACES))
        self.assertEqual(summary["cities"], 1)
        self.assertEqual(summary["popular_destinations"], 1)

    def test_three_day_itinerary_has_places_and_maps_for_every_day(self) -> None:
        itinerary = demo_itinerary("Paris", days=3, max_places=3)

        self.assertEqual(len(itinerary), 3)
        self.assertTrue(all(len(day["places"]) == 3 for day in itinerary))
        self.assertTrue(all(place["lat"] and place["lon"] for day in itinerary for place in day["places"]))

    def test_interest_filter_still_fills_each_requested_day(self) -> None:
        itinerary = demo_itinerary("Paris", days=3, max_places=2, categories=["Art"])

        self.assertTrue(all(day["places"] for day in itinerary))
        self.assertTrue(all("Art" in place["categories"] for day in itinerary for place in day["places"]))


if __name__ == "__main__":
    unittest.main()
