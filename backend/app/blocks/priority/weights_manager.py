"""Управление весами факторов приоритета (уровень L2)."""

from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

WEIGHTS_PATH = Path(__file__).resolve().parent / "weights.yaml"

EXPECTED_KEYS = ("HZ", "DM", "AG", "SP", "RC", "WX", "VF", "EX")

DEFAULT_WEIGHTS: dict[str, float] = {
    "HZ": 0.25,
    "DM": 0.15,
    "AG": 0.15,
    "SP": 0.15,
    "RC": 0.10,
    "WX": 0.05,
    "VF": 0.05,
    "EX": 0.10,
}


def get_weights() -> dict[str, float]:
    """Возвращает текущие веса факторов приоритета из weights.yaml."""
    weights = DEFAULT_WEIGHTS.copy()
    if WEIGHTS_PATH.is_file():
        try:
            data = yaml.safe_load(WEIGHTS_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                for k in EXPECTED_KEYS:
                    if k in data and isinstance(data[k], (int, float)) and data[k] >= 0:
                        weights[k] = float(data[k])
        except Exception:
            pass
    return weights


def update_weights(new_weights: dict[str, Any]) -> None:
    """Валидирует и обновляет веса факторов приоритета в weights.yaml.

    Бросает ValueError при отсутствии любого из обязательных ключей,
    нечисловых значениях или отрицательных весах.
    """
    for key in EXPECTED_KEYS:
        if key not in new_weights:
            raise ValueError(f"Missing key: {key}")

    for key, val in new_weights.items():
        if key not in EXPECTED_KEYS:
            raise ValueError(f"Unknown key: {key}")
        if not isinstance(val, (int, float)) or isinstance(val, bool):
            raise ValueError(f"Weight for {key} must be a number")
        if val < 0.0:
            raise ValueError(f"Weight for {key} must be >= 0")

    validated: dict[str, float] = {k: float(new_weights[k]) for k in EXPECTED_KEYS}

    lines = [f"{k}: {validated[k]}\n" for k in EXPECTED_KEYS]
    WEIGHTS_PATH.write_text("".join(lines), encoding="utf-8")
