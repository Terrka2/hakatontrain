"""L0: детерминированно, без сети, без ключей, без базы. Работает на fixture demo_city.json."""

import csv
import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from app.contracts.models import CATEGORIES, GeoPoint, Report

FIXTURE_PATH = Path(__file__).resolve().parents[2] / "fixtures" / "demo_city.json"


def load_fixture() -> list[Report]:
    """Загружает обращения из demo_city.json."""
    raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return [Report(**r) for r in raw["reports"]]


def _extract_location(
    mapped: dict[str, Any],
    *,
    allow_geocoding: bool = False,
    geocode_fn: Callable[[str], GeoPoint | None] | None = None,
) -> GeoPoint:
    """Извлекает и валидирует координаты из mapped словаря."""
    loc = mapped.get("location")
    if isinstance(loc, GeoPoint):
        return loc
    if isinstance(loc, dict):
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
                if not (-90.0 <= lat_f <= 90.0 and -180.0 <= lon_f <= 180.0):
                    raise ValueError(
                        f"Coordinates out of bounds: lat={lat_f}, lon={lon_f}"
                    )
                return GeoPoint(lat=lat_f, lon=lon_f)
            except (ValueError, TypeError) as e:
                if not allow_geocoding:
                    raise ValueError(
                        f"Invalid coordinate format: lat={lat}, lon={lon}"
                    ) from e
        elif not allow_geocoding:
            raise ValueError("Missing coordinates: lat and lon required in location")

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
            if not (-90.0 <= lat_f <= 90.0 and -180.0 <= lon_f <= 180.0):
                raise ValueError(f"Coordinates out of bounds: lat={lat_f}, lon={lon_f}")
            return GeoPoint(lat=lat_f, lon=lon_f)
        except (ValueError, TypeError) as e:
            if not allow_geocoding:
                raise ValueError(
                    f"Invalid coordinate format: lat={lat}, lon={lon}"
                ) from e

    # Если координат нет, пробуем геокодирование адреса (для L2)
    if allow_geocoding:
        raw_address = mapped.get("address")
        address = (
            str(raw_address).strip()
            if raw_address is not None and str(raw_address).strip()
            else None
        )
        if not address:
            raise ValueError("Missing coordinates: lat and lon required")
        if geocode_fn is None:
            raise ImportError("B2 geocode port is not available")
        try:
            geocoded_loc = geocode_fn(address)
        except Exception as e:
            raise ValueError("geocoding_failed") from e
        if geocoded_loc is None or not isinstance(geocoded_loc, GeoPoint):
            raise ValueError("geocoding_failed")
        return geocoded_loc

    raise ValueError("Missing coordinates: lat and lon required")


def _build_report(
    raw: dict[str, Any],
    mapping: dict[str, str] | None = None,
    *,
    category_resolver: Callable[[Any], str] | None = None,
    allow_geocoding: bool = False,
    geocode_fn: Callable[[str], GeoPoint | None] | None = None,
) -> Report:
    """Общий хелпер построения Report из сырой строки с применением mapping."""
    map_dict = mapping or {}
    mapped: dict[str, Any] = {
        (map_dict.get(k.strip(), k.strip()) if isinstance(k, str) else k): (
            v.strip() if isinstance(v, str) else v
        )
        for k, v in raw.items()
    }

    # Валидация категории
    raw_cat = mapped.get("category")
    if category_resolver is not None:
        cat = category_resolver(raw_cat)
    else:
        if isinstance(raw_cat, str):
            raw_cat = raw_cat.strip().lower()
        if not raw_cat or raw_cat not in CATEGORIES:
            raise ValueError(f"Unknown or missing category: {raw_cat}")
        cat = raw_cat

    # Координаты
    location = _extract_location(
        mapped, allow_geocoding=allow_geocoding, geocode_fn=geocode_fn
    )

    # Текст
    text = mapped.get("text")
    if not text or not str(text).strip():
        raise ValueError("Missing or empty report text")
    text_str = str(text).strip()

    # created_at (строго timezone-aware UTC)
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

    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)

    # id (стабильный MD5 хеш, если не задан)
    raw_id = mapped.get("id")
    if raw_id and str(raw_id).strip():
        report_id = str(raw_id).strip()
    else:
        report_id = hashlib.md5(
            f"{text_str}{location.lat}{location.lon}{created_at}".encode()
        ).hexdigest()[:12]

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

    address = mapped.get("address")
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
        category=cat,
        text=text_str,
        lang=lang,
        location=location,
        address=str(address).strip() if address is not None else None,
        photo_url=str(photo_url).strip() if photo_url is not None else None,
        created_at=created_at,
        status=status,
        cluster_id=mapped.get("cluster_id"),
        confirmations=confirmations,
    )


def _parse_file_with_normalizer(
    path: Path,
    normalize_fn: Callable[[dict[str, Any]], Report],
) -> tuple[list[Report], list[dict[str, Any]]]:
    """Общий хелпер парсинга файлов CSV/JSON."""
    suffix = path.suffix.lower()
    if suffix not in (".json", ".csv"):
        return [], [{"row": 0, "reason": "unsupported_file_format"}]

    reports: list[Report] = []
    rejected: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    if not path.exists():
        if path == FIXTURE_PATH or path.name == "demo_city.json":
            for r in load_fixture():
                if r.id not in seen_ids:
                    seen_ids.add(r.id)
                    reports.append(r)
        return reports, rejected

    content = path.read_text(encoding="utf-8").strip()
    if not content:
        return reports, rejected

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
                report = normalize_fn(item)
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
                report = normalize_fn(row)
                if report.id in seen_ids:
                    continue
                seen_ids.add(report.id)
                reports.append(report)
            except ValueError as e:
                rejected.append({"row": idx, "reason": str(e)})

    return reports, rejected


def normalize(raw: dict[str, Any], mapping: dict[str, str]) -> Report:
    """Нормализует сырую запись в Report с применением mapping."""
    return _build_report(raw, mapping)


def parse_file(
    path: Path, mapping: dict[str, str] | None = None
) -> tuple[list[Report], list[dict[str, Any]]]:
    """Парсит файл (CSV/JSON), возвращая (reports, rejected)."""
    map_dict = mapping or {}
    return _parse_file_with_normalizer(path, lambda row: normalize(row, map_dict))
