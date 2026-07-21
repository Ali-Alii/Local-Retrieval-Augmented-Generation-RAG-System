import asyncio
import unittest

from backend.app.main import app, health


class BackendApiTests(unittest.TestCase):
    def test_health_contract_reports_streaming(self):
        self.assertEqual(asyncio.run(health()), {"status": "ok", "service": "sentinel-api", "streaming": True})

    def test_required_routes_are_registered(self):
        paths = {route.path for route in app.routes}
        self.assertIn("/api/v1/status", paths)
        self.assertIn("/api/v1/ask", paths)
        self.assertIn("/api/v1/ask/stream", paths)
        self.assertIn("/api/v1/feedback", paths)


if __name__ == "__main__":
    unittest.main()
