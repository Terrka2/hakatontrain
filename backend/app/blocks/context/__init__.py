"""Блок B5 · Контекст: погода и соц. объекты. Порт блока — только то, что объявлено в этом файле.

Контракт: docs/contracts/B5_context.md. Реализация: l0.py (заглушка), l1.py (целевой уровень).
"""

import logging
from datetime import datetime

from app.contracts.models import Context, Decision, GeoPoint, Job, Weather
from app.core.config import settings

from . import l0, l1
from .l0 import reset_scenario, set_scenario

log = logging.getLogger(__name__)

__all__ = [
    "apply_weather_rules",
    "build_context",
    "get_weather",
    "reset_scenario",
    "set_scenario",
]


def get_weather(point: GeoPoint, at: datetime) -> Weather | None:
    if settings.WEATHER == "open-meteo":
        try:
            return l1.get_weather(point, at)
        except Exception:  # noqa: BLE001
            log.warning("B5: L1 failed, falling back to L0", exc_info=True)
    return l0.get_weather(point, at)


def build_context(now: datetime) -> Context:
    return l0.build_context(now)


def apply_weather_rules(
    jobs: list[Job], weather: Weather | None
) -> tuple[list[Job], list[Decision]]:
    return l0.apply_weather_rules(jobs, weather)
