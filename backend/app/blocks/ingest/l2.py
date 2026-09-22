"""L2: целевой уровень парсера и импорта с геокодированием адресов через блок B2."""

import csv
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from app.contracts.models import GeoPoint, Report

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

        if hasattr(geo, "geocode"):
            return geo.geocode
    except ImportError:
        pass
    return _geocode


def load_fixture() -> list[Report]:
    """Загрузка fixture (делегирует в l1/l0, геокодирование не требуется)."""
    return l1.load_fixture()


def normalize(raw: dict[str, Any], mapping: dict[str, str] | None = None) -> Report:
    """Нормализует сырую запись в Report с применением mapping, synonyms и геокодирования B2.

    Если координаты отсутствуют или невалидны, но передан непустой адрес:
    производится геокодирование через app.blocks.geo.geocode.
    При неудаче геокодирования (None, исключение или недоступность B2) бросается
    ValueError("geocoding_failed").
    """
    merged_mapping = dict(l1.get_default_mapping())
    if mapping:
        for k, v in mapping.items():
            merged_mapping[k.strip()] = v.strip()

    mapped: dict[str, Any] = {
        (merged_mapping.get(k.strip(), k.strip()) if isinstance(k, str) else k): (
            v.strip() if isinstance(v, str) else v
        )
        for k, v in raw.items()
    }

    # Категория (через словарь синонимов)
    raw_category = mapped.get("category")
    category = l1.resolve_category(raw_category)

    # Извлечение координат (если уже заданы валидно)
    loc = mapped.get("location")
    location: GeoPoint | None = None

    if isinstance(loc, GeoPoint):
        location = loc
    elif isinstance(loc, dict):
        lat = loc.get("lat")
        lon = loc.get("lon")
        if (
            lat is not None
            and lon is not None
            and not (isinstance(lat, str) and not lat.strip())
            and not (isinstance(lon, str) and not lon.strip())
        ):
            try:
                lat_f = float(lat)
                lon_f = float(lon)
                if -90.0 <= lat_f <= 90.0 and -180.0 <= lon_f <= 180.0:
                    location = GeoPoint(lat=lat_f, lon=lon_f)
            except ValueError, TypeError:
                location = None
    else:
        lat = mapped.get("lat")
        lon = mapped.get("lon")
        if (
            lat is not None
            and lon is not None
            and not (isinstance(lat, str) and not lat.strip())
            and not (isinstance(lon, str) and not lon.strip())
        ):
            try:
                lat_f = float(lat)
                lon_f = float(lon)
                if -90.0 <= lat_f <= 90.0 and -180.0 <= lon_f <= 180.0:
                    location = GeoPoint(lat=lat_f, lon=lon_f)
            except ValueError, TypeError:
                location = None

    # Адрес
    raw_address = mapped.get("address")
    address = (
        str(raw_address).strip()
        if raw_address is not None and str(raw_address).strip()
        else None
    )

    # Если координат нет или они невалидны — пробуем геокодирование через B2
    if location is None:
        if not address:
            raise ValueError("Missing coordinates: lat and lon required")

        geocoder = _get_geocoder()
        if geocoder is None:
            raise ImportError("B2 geocode port is not available")

        try:
            geocoded_loc = geocoder(address)
        except Exception as e:
            log.warning("B2 geocode failed for address '%s': %s", address, e)
            raise ValueError("geocoding_failed") from e

        if geocoded_loc is None or not isinstance(geocoded_loc, GeoPoint):
            raise ValueError("geocoding_failed")

        location = geocoded_loc

    # Текст обращения
    text = mapped.get("text")
    if not text or not str(text).strip():
        raise ValueError("Missing or empty report text")
    text_str = str(text).strip()

    # created_at
    created_at_val = mapped.get("created_at")
    if isinstance(created_at_val, datetime):
        created_at = created_at_val
    elif isinstance(created_at_val, str) and created_at_val.strip():
        try:
            created_at = datetime.fromisoformat(created_at_val.strip())
        except ValueError as e:
            raise ValueError(f"Invalid created_at datetime: {created_at_val}") from e
    else:
        created_at = datetime.now(UTC)

    # id
    raw_id = mapped.get("id")
    report_id = (
        str(raw_id).strip()
        if raw_id and str(raw_id).strip()
        else f"r_{uuid4().hex[:8]}"
    )

    # status
    status_val = mapped.get("status")
    status: Literal["open", "in_progress", "resolved", "rejected"] = (
        status_val
        if status_val in ("open", "in_progress", "resolved", "rejected")
        else "open"
    )

    # confirmations
    confirmations_val = mapped.get("confirmations", 0)
    try:
        confirmations = int(confirmations_val)
    except ValueError, TypeError:
        confirmations = 0

    photo_url = mapped.get("photo_url")
    source = mapped.get("source", "dataset")
    if source not in ("dataset", "citizen", "voice"):
        source = "dataset"
    lang = mapped.get("lang")
    if lang not in ("ro", "ru", "en"):
        lang = None

    return Report(
        id=report_id,
        source=source,
        category=category,
        text=text_str,
        lang=lang,
        location=location,
        address=address,
        photo_url=str(photo_url).strip() if photo_url is not None else None,
        created_at=created_at,
        status=status,
        cluster_id=mapped.get("cluster_id"),
        confirmations=confirmations,
    )


def parse_file(
    path: Path, mapping: dict[str, str] | None = None
) -> tuple[list[Report], list[dict[str, Any]]]:
    """Парсит CSV или JSON с применением mapping.yaml, synonyms.yaml и геокодирования B2."""
    if _get_geocoder() is None:
        raise ImportError("B2 geocode port is not available")

    reports: list[Report] = []
    rejected: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    if not path.exists():
        return reports, rejected

    content = path.read_text(encoding="utf-8").strip()
    if not content:
        return reports, rejected

    suffix = path.suffix.lower()

    if suffix == ".json":
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            rejected.append({"row": 0, "reason": f"Invalid JSON syntax: {e}"})
            return reports, rejected

        items: list[Any] = []
        if isinstance(data, dict):
            if "reports" in data and isinstance(data["reports"], list):
                items = data["reports"]
            else:
                items = [data]
        elif isinstance(data, list):
            items = data

        for idx, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                rejected.append({"row": idx, "reason": "Item must be a JSON object"})
                continue
            try:
                report = normalize(item, mapping)
                if report.id in seen_ids:
                    continue
                seen_ids.add(report.id)
                reports.append(report)
            except ValueError as e:
                rejected.append({"row": idx, "reason": str(e)})

    elif suffix == ".csv":
        reader = csv.DictReader(content.splitlines())
        for idx, row in enumerate(reader, start=1):
            try:
                report = normalize(row, mapping)
                if report.id in seen_ids:
                    continue
                seen_ids.add(report.id)
                reports.append(report)
            except ValueError as e:
                rejected.append({"row": idx, "reason": str(e)})

    else:
        # Для других форматов откат на l0
        return l0.parse_file(path, mapping)

    return reports, rejected
