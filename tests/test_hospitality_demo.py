import unittest

from hospitality_demo.pipeline import (
    load_source_records,
    recommendations,
    resolve_entities,
    run_demo_pipeline,
)


class HospitalityDemoPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = load_source_records()
        cls.canonical, cls.pairs = resolve_entities(cls.records)

    def test_resolves_twelve_source_rows_to_five_properties(self):
        self.assertEqual(len(self.records), 12)
        self.assertEqual(len(self.canonical), 5)

    def test_every_canonical_property_preserves_source_lineage(self):
        for property_record in self.canonical:
            self.assertEqual(property_record["source_count"], len(property_record["source_records"]))
            self.assertTrue(property_record["canonical_id"].startswith("acc_"))

    def test_harbour_grand_is_matched_across_three_sources(self):
        harbour = next(item for item in self.canonical if item["name"] == "Harbour Grand Hotel Ghent")
        self.assertEqual(harbour["source_count"], 3)
        self.assertEqual(harbour["minimum_rate"], 189.0)
        self.assertEqual(harbour["maximum_rate"], 215.0)
        self.assertGreater(harbour["rate_spread_pct"], 10)

    def test_recommendations_are_explainable(self):
        actions = recommendations(self.canonical)
        harbour_action = next(item for item in actions if item["property"] == "Harbour Grand Hotel Ghent")
        self.assertEqual(harbour_action["action"], "Review channel rate parity")
        self.assertIn("EUR 189", harbour_action["reason"])

    def test_quality_report_detects_stale_observation(self):
        result = run_demo_pipeline()
        stale = [issue for issue in result["quality_issues"] if issue["check"] == "freshness_72h"]
        self.assertEqual(len(stale), 1)
        self.assertEqual(stale[0]["record_id"], "TH-BE-497")


if __name__ == "__main__":
    unittest.main()
