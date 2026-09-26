import os
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.telegram import TelegramNotificationError, send_telegram_notification


class TelegramNotificationTests(unittest.TestCase):
    def test_sends_existing_optional_lead_fields(self):
        lead = SimpleNamespace(
            name="Test Customer",
            phone="0912345678",
            service_slug="bep-da",
            area="Quang Ngai",
            stone_type=None,
            expected_size=None,
            message="Please call in the afternoon",
        )
        response = Mock(status_code=200)
        response.json.return_value = {"ok": True}

        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test-token", "TELEGRAM_CHAT_ID": "-100"}), patch(
            "app.telegram.httpx.post", return_value=response
        ) as post:
            send_telegram_notification(lead)

        args, kwargs = post.call_args
        self.assertEqual(args[0], "https://api.telegram.org/bottest-token/sendMessage")
        self.assertEqual(kwargs["timeout"], 5.0)
        self.assertIn("👤 Khách hàng: Test Customer", kwargs["json"]["text"])
        self.assertIn("🏠 Hạng mục: bep-da", kwargs["json"]["text"])
        self.assertNotIn("Loại đá", kwargs["json"]["text"])

    def test_telegram_failure_does_not_fail_saved_lead(self):
        session = Mock()
        session_context = Mock()
        session_context.__enter__ = Mock(return_value=session)
        session_context.__exit__ = Mock(return_value=False)

        with patch.dict(os.environ, {"RATE_LIMIT_SALT": "test-salt", "TURNSTILE_SECRET_KEY": "test-secret"}), patch(
            "app.main.Base.metadata.create_all"
        ), patch("app.main.SessionLocal", return_value=session_context), patch(
            "app.main.check_rate_limit"
        ), patch("app.main.verify_turnstile"), patch(
            "app.main.send_telegram_notification", side_effect=RuntimeError("Telegram unavailable")
        ):
            session.refresh.side_effect = lambda lead: setattr(
                lead, "created_at", datetime.now(timezone.utc)
            )
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/leads",
                    json={"name": "Test Customer", "phone": "0912345678", "turnstile_token": "test-token"},
                )

        self.assertEqual(response.status_code, 201)
        session.commit.assert_called_once()

    def test_rejects_unsuccessful_telegram_response(self):
        response = Mock(status_code=200)
        response.json.return_value = {"ok": False}
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test-token", "TELEGRAM_CHAT_ID": "-100"}), patch(
            "app.telegram.httpx.post", return_value=response
        ), self.assertRaises(TelegramNotificationError):
            send_telegram_notification(
                SimpleNamespace(
                    name="A",
                    phone="123",
                    service_slug=None,
                    area=None,
                    stone_type=None,
                    expected_size=None,
                    message=None,
                )
            )


if __name__ == "__main__":
    unittest.main()
