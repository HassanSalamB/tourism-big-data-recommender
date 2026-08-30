from __future__ import annotations

import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "src" / "api" / "dashboard.py"


class DashboardNavigationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = DASHBOARD.read_text(encoding="utf-8")

    def test_itinerary_app_is_the_default_root_page(self):
        self.assertIn(
            'APP_PAGE = st.Page(itinerary_page, title="Itinerary App", icon="🧭", default=True)',
            self.source,
        )
        self.assertNotIn(
            'HOME_PAGE = st.Page(home_page, title="Project Home", icon="🏠", default=True)',
            self.source,
        )

    def test_project_and_architecture_pages_are_grouped_under_details(self):
        self.assertIn(
            '"Details": [HOME_PAGE, ARCHITECTURE_PAGE, PIPELINE_PAGE, SERVING_PAGE, OBSERVABILITY_PAGE, RUNBOOK_PAGE]',
            self.source,
        )

    def test_portfolio_link_uses_the_hsb_brand_icon(self):
        self.assertIn("https://hassansalamb.dev/favicon.svg?v=2", self.source)
        self.assertNotIn(">⌂</a>", self.source)


if __name__ == "__main__":
    unittest.main()
