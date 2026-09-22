"""L0: детерминированно, без сети, без ключей, без базы. Работает на fixture demo_city.json."""

import csv
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from app.contracts.models import CATEGORIES, GeoPoint, Report

FIXTURE_PATH = Path(__file__).resolve().parents[2] / "fixtures" / "demo_city.json"

_store: dict[str, Report] | None = None


def get_store() -> dict[str, Report]:
    """Возвращает in-memory реестр обращений, инициализированный из fixture."""
    global _store
    if _store is None:
        reports = load_fixture()
        _store = {r.id: r for r in reports}
    return _store


def reset_store() -> None:
    """Сбрасывает in-memory реестр для изоляции тестов."""
    global _store
    _store = None


def load_fixture() -> list[Report]:
    """Загружает обращения из demo_city.json."""
    raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return [Report(**r) for r in raw["reports"]]


def normalize(raw: dict[str, Any], mapping: dict[str, str]) -> Report:
    """Нормализует сырую запись в Report с применением mapping.

    Бросает ValueError с понятной причиной при невалидных данных.
    """
    mapped: dict[str, Any] = {
        (mapping.get(k.strip(), k.strip()) if isinstance(k, str) else k): (
            v.strip() if isinstance(v, str) else v
        )
        for k, v in raw.items()
    }

    cat = mapped.get("category")
    if isinstance(cat, str):
        cat = cat.strip().lower()
    if not cat or cat not in CATEGORIES:
        raise ValueError(f"Unknown or missing category: {cat}")

    loc = mapped.get("location")
    if isinstance(loc, GeoPoint):
        location = loc
    elif isinstance(loc, dict):
        lat = loc.get("lat")
        lon = loc.get("lon")
        if (
            lat is None
            or lon is None
            or (isinstance(lat, str) and not lat.strip())
            or (isinstance(lon, str) and not lon.strip())
        ):
            raise ValueError("Missing coordinates: lat and lon required in location")
        try:
            lat_f = float(lat)
            lon_f = float(lon)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid coordinate format: lat={lat}, lon={lon}") from e
        if not (-90.0 <= lat_f <= 90.0 and -180.0 <= lon_f <= 180.0):
            raise ValueError(f"Coordinates out of bounds: lat={lat_f}, lon={lon_f}")
        location = GeoPoint(lat=lat_f, lon=lon_f)
    else:
        lat = mapped.get("lat")
        lon = mapped.get("lon")
        if (
            lat is None
            or lon is None
            or (isinstance(lat, str) and not lat.strip())
            or (isinstance(lon, str) and not lon.strip())
        ):
            raise ValueError("Missing coordinates: lat and lon required")
        try:
            lat_f = float(lat)
            lon_f = float(lon)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid coordinate format: lat={lat}, lon={lon}") from e
        if not (-90.0 <= lat_f <= 90.0 and -180.0 <= lon_f <= 180.0):
            raise ValueError(f"Coordinates out of bounds: lat={lat_f}, lon={lon_f}")
        location = GeoPoint(lat=lat_f, lon=lon_f)

    text = mapped.get("text")
    if not text or not str(text).strip():
        raise ValueError("Missing or empty report text")
    text_str = str(text).strip()

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

    raw_id = mapped.get("id")
    report_id = (
        str(raw_id).strip()
        if raw_id and str(raw_id).strip()
        else f"r_{uuid4().hex[:8]}"
    )

    status_val = mapped.get("status")
    status: Literal["open", "in_progress", "resolved", "rejected"] = (
        status_val
        if status_val in ("open", "in_progress", "resolved", "rejected")
        else "open"
    )

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


def parse_file(
    path: Path, mapping: dict[str, str] | None = None
) -> tuple[list[Report], list[dict[str, Any]]]:
    """Парсит файл (CSV/JSON), возвращая (reports, rejected).

    Повторные записи с одинаковым id не создают дубликатов.
    Невалидные строки добавляются в rejected с номером строки и причиной.
    """
    map_dict = mapping or {}
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
                report = normalize(item, map_dict)
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
                report = normalize(row, map_dict)
                if report.id in seen_ids:
                    continue
                seen_ids.add(report.id)
                reports.append(report)
            except ValueError as e:
                rejected.append({"row": idx, "reason": str(e)})

    else:
        # Fallback для неопознанного расширения
        for r in load_fixture():
            if r.id not in seen_ids:
                seen_ids.add(r.id)
                reports.append(r)

    return reports, rejected
