import unittest
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from app.main import app


class LeadSecurityTests(unittest.TestCase):
    def test_validation_and_rate_limit(self):
        payload = {"name": "Test User", "phone": "0912345678", "turnstile_token": "XXXX.DUMMY.TOKEN.XXXX"}
        with TestClient(app) as client:
            self.assertEqual(client.get("/health").status_code, 200)
            self.assertEqual(client.get("/ready").status_code, 200)
            self.assertEqual(client.post("/api/v1/leads", json={**payload, "turnstile_token": ""}).status_code, 422)
            self.assertEqual(client.post("/api/v1/leads", content=b"x" * 8193).status_code, 413)

            with patch("app.security.httpx.post", return_value=Mock(status_code=200, json=lambda: {"success": False})):
                self.assertEqual(client.post("/api/v1/leads", json=payload).status_code, 422)

            with patch("app.security.httpx.post", return_value=Mock(status_code=200, json=lambda: {"success": True})):
                for _ in range(4):
                    self.assertEqual(client.post("/api/v1/leads", json=payload).status_code, 201)
                self.assertEqual(client.post("/api/v1/leads", json=payload).status_code, 429)


if __name__ == "__main__":
    unittest.main()
