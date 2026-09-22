"""L1: целевой уровень парсера и импорта обращений.

Парсит CSV и JSON с использованием mapping.yaml и synonyms.yaml (RO/RU/EN).
"""

import csv
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

import yaml  # type: ignore[import-untyped]

from app.contracts.models import CATEGORIES, GeoPoint, Report

from . import l0

DEFAULT_MAPPING_PATH = Path(__file__).resolve().parent / "mapping.yaml"
SYNONYMS_PATH = Path(__file__).resolve().parent / "synonyms.yaml"

_cached_mapping: dict[str, str] | None = None
_cached_synonyms: dict[str, str] | None = None


def get_default_mapping() -> dict[str, str]:
    """Загружает базовый маппинг колонок из mapping.yaml."""
    global _cached_mapping
    if _cached_mapping is None:
        if DEFAULT_MAPPING_PATH.exists():
            data = yaml.safe_load(DEFAULT_MAPPING_PATH.read_text(encoding="utf-8"))
            _cached_mapping = (
                {str(k).strip(): str(v).strip() for k, v in data.items()}
                if isinstance(data, dict)
                else {}
            )
        else:
            _cached_mapping = {}
    return _cached_mapping


def get_synonyms_map() -> dict[str, str]:
    """Загружает словарь синонимов из synonyms.yaml и строит lookup-таблицу."""
    global _cached_synonyms
    if _cached_synonyms is None:
        lookup: dict[str, str] = {}
        # Сначала регистрируем сами канонические категории
        for cat in CATEGORIES:
            lookup[cat.lower()] = cat

        if SYNONYMS_PATH.exists():
            data = yaml.safe_load(SYNONYMS_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                for canonical, syns in data.items():
                    if canonical in CATEGORIES and isinstance(syns, list):
                        for s in syns:
                            s_str = str(s).strip().lower()
                            lookup[s_str] = canonical
                            # Вариант с подчеркиваниями вместо пробелов и дефисов
                            normalized_s = s_str.replace(" ", "_").replace("-", "_")
                            lookup[normalized_s] = canonical
                            # Вариант с пробелами вместо подчеркиваний
                            lookup[s_str.replace("_", " ")] = canonical
        _cached_synonyms = lookup
    return _cached_synonyms


def resolve_category(raw_cat: Any) -> str:
    """Приводит категорию к каноническому значению CATEGORIES через таблицу синонимов."""
    if not raw_cat:
        raise ValueError("Category cannot be empty")

    cat_str = str(raw_cat).strip().lower()
    synonyms = get_synonyms_map()

    # 1. Прямое совпадение
    if cat_str in synonyms:
        return synonyms[cat_str]

    # 2. Совпадение с заменой пробелов/дефисов на _
    var1 = cat_str.replace(" ", "_").replace("-", "_")
    if var1 in synonyms:
        return synonyms[var1]

    # 3. Совпадение с заменой _ на пробелы
    var2 = cat_str.replace("_", " ")
    if var2 in synonyms:
        return synonyms[var2]

    raise ValueError(f"Unknown category: '{raw_cat}'")


def load_fixture() -> list[Report]:
    """Загрузка fixture (делегирует в l0)."""
    return l0.load_fixture()


def normalize(raw: dict[str, Any], mapping: dict[str, str] | None = None) -> Report:
    """Нормализует сырую запись в Report с применением mapping.yaml и synonyms.yaml.

    Бросает ValueError при невалидных данных (нет координат, неизвестная категория).
    """
    merged_mapping = dict(get_default_mapping())
    if mapping:
        for k, v in mapping.items():
            merged_mapping[k.strip()] = v.strip()

    mapped: dict[str, Any] = {
        (merged_mapping.get(k.strip(), k.strip()) if isinstance(k, str) else k): (
            v.strip() if isinstance(v, str) else v
        )
        for k, v in raw.items()
    }

    # Валидация и нормализация категории
    raw_category = mapped.get("category")
    category = resolve_category(raw_category)

    # Валидация координат
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

    # Валидация текста
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
        category=category,
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
    """Парсит CSV или JSON с применением mapping.yaml и synonyms.yaml."""
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
        # Для других файлов откат на l0
        return l0.parse_file(path, mapping)

    return reports, rejected
