import unittest

from src.api.service_registry import (
    ServiceEndpoint,
    backend_status_message,
    load_backend_status,
    load_service_registry,
    service_call_to_action,
)


class ServiceRegistryTest(unittest.TestCase):
    def test_status_defaults_to_recorded(self):
        self.assertEqual(load_backend_status({}), "recorded")

    def test_status_rejects_unknown_value(self):
        with self.assertRaisesRegex(ValueError, "BACKEND_ENVIRONMENT_STATUS"):
            load_backend_status({"BACKEND_ENVIRONMENT_STATUS": "online"})

    def test_registry_normalizes_present_urls_and_ignores_blanks(self):
        services = load_service_registry(
            {
                "SERVICE_AIRFLOW_URL": " https://airflow.example.com/ ",
                "SERVICE_GRAFANA_URL": " ",
            }
        )
        self.assertEqual(services["airflow"].url, "https://airflow.example.com")
        self.assertIsNone(services["grafana"].url)

    def test_live_service_gets_live_action(self):
        endpoint = ServiceEndpoint(
            "Airflow", "SERVICE_AIRFLOW_URL", "https://airflow.example.com"
        )
        self.assertEqual(
            service_call_to_action("live", endpoint),
            ("Open live Airflow", "https://airflow.example.com"),
        )

    def test_recorded_or_missing_service_has_no_live_action(self):
        endpoint = ServiceEndpoint("Airflow", "SERVICE_AIRFLOW_URL", None)
        self.assertIsNone(service_call_to_action("recorded", endpoint))
        self.assertIsNone(service_call_to_action("maintenance", endpoint))
        self.assertIsNone(service_call_to_action("live", endpoint))

    def test_maintenance_status_explains_fallback(self):
        css_class, heading, message = backend_status_message("maintenance")
        self.assertEqual(css_class, "notice")
        self.assertEqual(heading, "Engineering environment in maintenance")
        self.assertIn("Recorded evidence remains available", message)

    def test_all_required_services_exist(self):
        services = load_service_registry({})
        self.assertEqual(
            set(services),
            {
                "streamlit",
                "fastapi",
                "airflow",
                "kafka",
                "spark",
                "grafana",
                "prometheus",
                "neo4j",
                "adminer",
            },
        )


if __name__ == "__main__":
    unittest.main()
