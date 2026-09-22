"""Фактор WX: Погода (вес 0.05).

tree при ветре >= 15 м/с -> 1.0;
water_leak при t <= 0 -> 1.0;
иначе 0.
Нет погоды -> None.
"""

from app.contracts.models import Cluster, Context, Report


def evaluate(
    cluster: Cluster, reports: list[Report], history: list[Report], ctx: Context
) -> tuple[float | None, list[str]]:
    _ = (reports, history)
    if ctx.weather is None:
        return (None, [])

    cat = cluster.category.lower()
    if cat == "tree" and ctx.weather.wind_ms >= 15.0:
        return (
            1.0,
            [
                f"Повышенная опасность для 'tree': скорость ветра {ctx.weather.wind_ms:.1f} м/с (≥ 15 м/с)"
            ],
        )

    if cat == "water_leak" and ctx.weather.temp_c <= 0.0:
        return (
            1.0,
            [
                f"Опасность обледенения для 'water_leak': температура {ctx.weather.temp_c:.1f}°C (≤ 0°C)"
            ],
        )

    return (0.0, [])
