import unittest

from src.api.dashboard_demo import PLACES, WEATHER, demo_cities, demo_summary


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


if __name__ == "__main__":
    unittest.main()
