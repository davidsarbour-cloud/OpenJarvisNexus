"""Telegram notifier — fire-and-forget alerts to David's chat.

Reuses Nexus9's bot (TELEGRAM_BOT_TOKEN + TELEGRAM_AUTHORIZED_USER_ID). No-op
and never raises if unconfigured or unreachable — an alert failing must never
take down the trading loop. Used for: daily-loss circuit breaker, HALT toggles,
and propose-only tuning suggestions.
"""
from __future__ import annotations

from shared.config import SETTINGS


async def send_telegram(text: str) -> bool:
    """Send a message. Returns True on success, False on no-op/failure. Never raises."""
    if not SETTINGS.telegram_token or not SETTINGS.telegram_chat_id:
        return False
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(
                f"https://api.telegram.org/bot{SETTINGS.telegram_token}/sendMessage",
                json={"chat_id": SETTINGS.telegram_chat_id, "text": text,
                      "disable_web_page_preview": True},
            )
            return r.status_code == 200
    except Exception:
        return False
