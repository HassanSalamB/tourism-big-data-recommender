from __future__ import annotations

import json
import pathlib
import subprocess
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class LocalConfigurationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        result = subprocess.run(
            [
                "docker",
                "compose",
                "--env-file",
                str(ROOT / ".env.example"),
                "config",
                "--format",
                "json",
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        cls.config = json.loads(result.stdout)

    def test_application_modules_share_one_image(self):
        services = self.config["services"]
        expected = services["api"]["image"]
        self.assertEqual(services["dashboard"]["image"], expected)
        self.assertEqual(services["kafka-analytics-consumer"]["image"], expected)

    def test_airflow_modules_share_one_image(self):
        services = self.config["services"]
        expected = services["airflow-webserver"]["image"]
        self.assertEqual(services["airflow-scheduler"]["image"], expected)
        self.assertEqual(services["airflow-init"]["image"], expected)
        self.assertEqual(services["dbt"]["image"], expected)

    def test_third_party_images_are_versioned(self):
        for name, service in self.config["services"].items():
            image = service.get("image")
            if image is None:
                continue
            with self.subTest(service=name, image=image):
                self.assertNotEqual(image.rsplit(":", 1)[-1], "latest")


if __name__ == "__main__":
    unittest.main()
