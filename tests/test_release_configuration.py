from __future__ import annotations

import json
import os
import pathlib
import subprocess
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
COMPOSE_FILE = ROOT / "distribution" / "compose.release.yml"
ENV_EXAMPLE = ROOT / "distribution" / ".env.example"
class ReleaseConfigurationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        environment = os.environ.copy()
        environment["CLOUDFLARE_TUNNEL_TOKEN"] = "test-token"
        environment["SERVICE_ENV_FILE"] = ".env.example"
        result = subprocess.run(
            [
                "docker",
                "compose",
                "--env-file",
                str(ENV_EXAMPLE),
                "-f",
                str(COMPOSE_FILE),
                "--profile",
                "tunnel",
                "config",
                "--format",
                "json",
            ],
            cwd=ROOT,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )
        cls.config = json.loads(result.stdout)

    def test_published_ports_bind_to_loopback(self):
        published_ports = [
            port
            for service in self.config["services"].values()
            for port in service.get("ports", [])
        ]
        self.assertTrue(published_ports)
        self.assertTrue(
            all(port.get("host_ip") == "127.0.0.1" for port in published_ports)
        )

    def test_data_plane_ports_are_not_published(self):
        forbidden = {
            ("postgres", 5432),
            ("kafka", 9092),
            ("kafka", 9094),
            ("neo4j", 7687),
            ("spark-master", 7077),
            ("kafka-analytics-consumer", 9108),
        }
        published = {
            (service_name, int(port["target"]))
            for service_name, service in self.config["services"].items()
            for port in service.get("ports", [])
        }
        self.assertTrue(forbidden.isdisjoint(published))

    def test_tunnel_is_profiled_and_token_driven(self):
        tunnel = self.config["services"]["cloudflared"]
        self.assertIn("test-token", " ".join(tunnel["command"]))
        self.assertEqual(tunnel["restart"], "unless-stopped")

    def test_long_running_services_have_runtime_limits(self):
        long_running = set(self.config["services"]) - {"airflow-init"}
        for name in long_running:
            with self.subTest(service=name):
                service = self.config["services"][name]
                self.assertEqual(service.get("restart"), "unless-stopped")
                self.assertGreater(int(service.get("mem_limit", 0)), 0)
                self.assertEqual(service.get("logging", {}).get("options", {}).get("max-size"), "10m")

    def test_images_are_versioned(self):
        for name, service in self.config["services"].items():
            image = service.get("image")
            if image is None:
                continue
            with self.subTest(service=name, image=image):
                self.assertNotEqual(image.rsplit(":", 1)[-1], "latest")

    def test_administrative_credentials_are_environment_driven(self):
        airflow_init = self.config["services"]["airflow-init"]
        airflow_command = " ".join(airflow_init["command"])
        self.assertNotIn("--password admin", airflow_command)
        self.assertNotIn("local-dev-secret", airflow_command)

        grafana_environment = self.config["services"]["grafana"]["environment"]
        self.assertNotEqual(grafana_environment["GF_SECURITY_ADMIN_PASSWORD"], "admin")

        airflow_environment = self.config["services"]["airflow-webserver"]["environment"]
        self.assertNotEqual(
            airflow_environment["AIRFLOW__WEBSERVER__SECRET_KEY"],
            "local-dev-secret",
        )


if __name__ == "__main__":
    unittest.main()
