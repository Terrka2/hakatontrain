"""L2: целевой уровень парсера и импорта с геокодированием адресов через блок B2."""

import logging
from pathlib import Path
from typing import Any

from app.contracts.models import Report

from . import l0, l1

log = logging.getLogger(__name__)

try:
    from app.blocks.geo import geocode as _geocode
except ImportError:
    _geocode = None  # type: ignore[assignment]


def _get_geocoder() -> Any:
    """Возвращает функцию geocode из B2 или None, если блок недоступен."""
    global _geocode
    if _geocode is None:
        return None

    try:
        from app.blocks import geo

        if hasattr(geo, "geocode") and geo.geocode is not None:
            fn = geo.geocode
            if getattr(fn, "__code__", None):
                if (
                    "NotImplementedError" in fn.__code__.co_names
                    and fn.__module__ == "app.blocks.geo"
                ):
                    return None
            return fn
    except ImportError:
        pass

    if getattr(_geocode, "__code__", None):
        if (
            "NotImplementedError" in _geocode.__code__.co_names
            and _geocode.__module__ == "app.blocks.geo"
        ):
            return None
    return _geocode


def is_geocoder_available() -> bool:
    """Проверяет доступность геокодера B2."""
    return _get_geocoder() is not None


def load_fixture() -> list[Report]:
    """Загрузка fixture (делегирует в l1/l0)."""
    return l1.load_fixture()


def normalize(raw: dict[str, Any], mapping: dict[str, str] | None = None) -> Report:
    """Нормализует сырую запись в Report с геокодированием адресов через B2."""
    geocoder = _get_geocoder()
    if geocoder is None:
        raise ImportError("B2 geocode port is not available")

    merged = dict(l1.get_default_mapping())
    if mapping:
        for k, v in mapping.items():
            merged[k.strip()] = v.strip()

    return l0._build_report(
        raw,
        merged,
        category_resolver=l1.resolve_category,
        allow_geocoding=True,
        geocode_fn=geocoder,
    )


def parse_file(
    path: Path, mapping: dict[str, str] | None = None
) -> tuple[list[Report], list[dict[str, Any]]]:
    """Парсит CSV или JSON с применением mapping.yaml, synonyms.yaml и геокодирования B2."""
    if _get_geocoder() is None:
        raise ImportError("B2 geocode port is not available")

    return l0._parse_file_with_normalizer(path, lambda row: normalize(row, mapping))
