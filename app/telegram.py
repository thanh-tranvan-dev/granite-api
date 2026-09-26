import os

import httpx

from app.models import Lead


class TelegramNotificationError(RuntimeError):
    pass


def send_telegram_notification(lead: Lead) -> None:
    """Send a saved quotation to the configured Telegram chat."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        raise TelegramNotificationError("Telegram credentials are not configured")

    lines = [
        "🔔 YÊU CẦU BÁO GIÁ MỚI",
        "",
        f"👤 Khách hàng: {lead.name}",
        f"📞 SĐT: {lead.phone}",
    ]
    optional_fields = (
        ("🏠 Hạng mục", lead.service_slug),
        ("📍 Khu vực", lead.area),
        ("🪨 Loại đá", lead.stone_type),
        ("📐 Kích thước dự kiến", lead.expected_size),
    )
    lines.extend(f"{label}: {value}" for label, value in optional_fields if value)
    if lead.message:
        lines.extend(("", "📝 Ghi chú:", lead.message))

    try:
        response = httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": "\n".join(lines)},
            timeout=5.0,
        )
        if response.status_code != 200:
            raise TelegramNotificationError(
                f"Telegram API returned HTTP {response.status_code}"
            )
        if not response.json().get("ok"):
            raise TelegramNotificationError("Telegram API rejected the message")
    except httpx.HTTPError as exc:
        # Do not include the request URL: it contains the bot token.
        raise TelegramNotificationError(
            f"Telegram request failed ({type(exc).__name__})"
        ) from None
    except ValueError:
        raise TelegramNotificationError("Telegram returned an invalid response") from None
