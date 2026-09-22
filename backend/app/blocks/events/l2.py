"""Уровень L2 блока X1: получение мероприятий из внешнего JSON API."""

import logging
import os
from datetime import datetime

import httpx

from app.contracts.models import Event

log = logging.getLogger(__name__)

EXTERNAL_EVENTS_URL = os.getenv("EVENTS_API_URL", "https://api.demo-city.local/events")


def fetch_external_events(start: datetime, end: datetime) -> list[Event]:
    """Получение мероприятий из внешнего JSON API с таймаутом 5 секунд.

    При любой ошибке сети, таймауте, невалидном статусе или JSON возвращает [].
    """
    params = {
        "start": start.isoformat(),
        "end": end.isoformat(),
    }
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(EXTERNAL_EVENTS_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
            if not isinstance(data, list):
                if isinstance(data, dict) and isinstance(data.get("events"), list):
                    data = data["events"]
                else:
                    raise ValueError(f"Invalid external events format: {type(data)}")
            return [Event.model_validate(item) for item in data]
    except Exception as exc:
        log.warning("X1 L2 external API failed: %s", exc, exc_info=True)
        return []
