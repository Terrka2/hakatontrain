"""Блок B5 · Контекст: погода и соц. объекты. Порт блока — только то, что объявлено в этом файле.

Контракт: docs/contracts/B5_context.md. Реализация: l0.py (заглушка), l1.py (целевой уровень).
"""

from datetime import datetime

from app.contracts.models import Context, Decision, GeoPoint, Job, Weather


def get_weather(point: GeoPoint, at: datetime) -> Weather | None:
    raise NotImplementedError("B5: реализуй по контракту docs/contracts/B5_context.md")


def build_context(now: datetime) -> Context:
    raise NotImplementedError("B5: реализуй по контракту docs/contracts/B5_context.md")


def apply_weather_rules(
    jobs: list[Job], weather: Weather | None
) -> tuple[list[Job], list[Decision]]:
    raise NotImplementedError("B5: реализуй по контракту docs/contracts/B5_context.md")
