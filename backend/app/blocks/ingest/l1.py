"""L1: целевой уровень парсера и импорта обращений.

Парсит CSV и JSON с использованием mapping.yaml и synonyms.yaml (RO/RU/EN).
"""

from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from app.contracts.models import CATEGORIES, Report

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
                            normalized_s = s_str.replace(" ", "_").replace("-", "_")
                            lookup[normalized_s] = canonical
                            lookup[s_str.replace("_", " ")] = canonical
        _cached_synonyms = lookup
    return _cached_synonyms


def resolve_category(raw_cat: Any) -> str:
    """Приводит категорию к каноническому значению CATEGORIES через таблицу синонимов."""
    if not raw_cat:
        raise ValueError("Category cannot be empty")

    cat_str = str(raw_cat).strip().lower()
    synonyms = get_synonyms_map()

    if cat_str in synonyms:
        return synonyms[cat_str]

    var1 = cat_str.replace(" ", "_").replace("-", "_")
    if var1 in synonyms:
        return synonyms[var1]

    var2 = cat_str.replace("_", " ")
    if var2 in synonyms:
        return synonyms[var2]

    raise ValueError(f"Unknown category: '{raw_cat}'")


def load_fixture() -> list[Report]:
    """Загрузка fixture (делегирует в l0)."""
    return l0.load_fixture()


def normalize(raw: dict[str, Any], mapping: dict[str, str] | None = None) -> Report:
    """Нормализует сырую запись в Report с применением mapping.yaml и synonyms.yaml."""
    merged = dict(get_default_mapping())
    if mapping:
        for k, v in mapping.items():
            merged[k.strip()] = v.strip()
    return l0._build_report(raw, merged, category_resolver=resolve_category)


def parse_file(
    path: Path, mapping: dict[str, str] | None = None
) -> tuple[list[Report], list[dict[str, Any]]]:
    """Парсит CSV или JSON с применением mapping.yaml и synonyms.yaml."""
    return l0._parse_file_with_normalizer(path, lambda row: normalize(row, mapping))
