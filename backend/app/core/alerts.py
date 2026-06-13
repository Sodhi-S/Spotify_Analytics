from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import requests

from app.core.config import get_settings


def send_slack_alert(source: str, summary: str, failed_records: int = 0) -> None:
    """Send a compact pipeline alert when a webhook is configured."""
    settings = get_settings()
    if not settings.slack_webhook_url:
        return

    payload: dict[str, Any] = {
        "text": (
            f"[{datetime.now(timezone.utc).isoformat()}] {source}: "
            f"{summary} | failed_records={failed_records}"
        )
    }
    response = requests.post(settings.slack_webhook_url, json=payload, timeout=10)
    response.raise_for_status()
