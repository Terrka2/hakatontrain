"""Тесты управления весами уровня L2 блока B4 (priority)."""

import json
from collections.abc import Generator
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from app.blocks import priority
from app.blocks.priority.weights_manager import (
    EXPECTED_KEYS,
    WEIGHTS_PATH,
)
from app.contracts.models import (
    Cluster,
    Context,
    Report,
)

FIXTURE_PATH = (
    Path(__file__).resolve().parents[3] / "app" / "fixtures" / "demo_city.json"
)


@pytest.fixture
def restore_weights() -> Generator[None]:
    """Сохраняет исходное состояние weights.yaml и восстанавливает его после теста."""
    original_text = WEIGHTS_PATH.read_text(encoding="utf-8")
    try:
        yield
    finally:
        WEIGHTS_PATH.write_text(original_text, encoding="utf-8")


@pytest.fixture
def fixture_data() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def reports_map(fixture_data: dict[str, Any]) -> dict[str, Report]:
    return {r["id"]: Report(**r) for r in fixture_data["reports"]}


@pytest.fixture
def base_context(fixture_data: dict[str, Any]) -> Context:
    return Context(
        now=datetime.fromisoformat(fixture_data["now"]),
        weather=None,
        events=[],
        infrastructure=[],
    )


def test_get_weights_returns_all_expected_keys() -> None:
    """get_weights() возвращает словарь со всеми 8 ожидаемыми факторами."""
    weights = priority.get_weights()
    assert set(weights.keys()) == set(EXPECTED_KEYS)
    for k in EXPECTED_KEYS:
        assert isinstance(weights[k], float)
        assert weights[k] >= 0.0


@pytest.mark.usefixtures("restore_weights")
def test_update_weights_success() -> None:
    """update_weights() успешно валидирует и записывает веса в weights.yaml."""
    new_w = {
        "HZ": 0.30,
        "DM": 0.10,
        "AG": 0.10,
        "SP": 0.20,
        "RC": 0.10,
        "WX": 0.05,
        "VF": 0.05,
        "EX": 0.10,
    }
    priority.update_weights(new_w)

    current_w = priority.get_weights()
    assert current_w["HZ"] == 0.30
    assert current_w["SP"] == 0.20

    file_content = WEIGHTS_PATH.read_text(encoding="utf-8")
    assert "HZ: 0.3" in file_content
    assert "SP: 0.2" in file_content


@pytest.mark.usefixtures("restore_weights")
def test_update_weights_missing_key() -> None:
    """update_weights() бросает ValueError при отсутствии любого из обязательных ключей."""
    incomplete_w = {
        "HZ": 0.30,
        "DM": 0.10,
        "AG": 0.10,
        "SP": 0.20,
        "RC": 0.10,
        "WX": 0.05,
        "VF": 0.05,
    }
    with pytest.raises(ValueError, match="Missing key: EX"):
        priority.update_weights(incomplete_w)


@pytest.mark.usefixtures("restore_weights")
def test_update_weights_negative_value() -> None:
    """update_weights() бросает ValueError при отрицательном значении веса."""
    invalid_w = {
        "HZ": -0.05,
        "DM": 0.15,
        "AG": 0.15,
        "SP": 0.15,
        "RC": 0.10,
        "WX": 0.05,
        "VF": 0.05,
        "EX": 0.10,
    }
    with pytest.raises(ValueError, match="Weight for HZ must be >= 0"):
        priority.update_weights(invalid_w)


@pytest.mark.usefixtures("restore_weights")
def test_update_weights_unknown_key() -> None:
    """update_weights() бросает ValueError при наличии неизвестного ключа."""
    invalid_w = {
        "HZ": 0.25,
        "DM": 0.15,
        "AG": 0.15,
        "SP": 0.15,
        "RC": 0.10,
        "WX": 0.05,
        "VF": 0.05,
        "EX": 0.10,
        "UNKNOWN": 0.05,
    }
    with pytest.raises(ValueError, match="Unknown key: UNKNOWN"):
        priority.update_weights(invalid_w)


@pytest.mark.usefixtures("restore_weights")
def test_update_weights_non_number_value() -> None:
    """update_weights() бросает ValueError при нечисловом значении."""
    invalid_w = {
        "HZ": "not_a_number",
        "DM": 0.15,
        "AG": 0.15,
        "SP": 0.15,
        "RC": 0.10,
        "WX": 0.05,
        "VF": 0.05,
        "EX": 0.10,
    }
    with pytest.raises(ValueError, match="must be a number"):
        priority.update_weights(invalid_w)


@pytest.mark.usefixtures("restore_weights")
def test_score_dynamically_uses_updated_weights(
    reports_map: dict[str, Report],
    base_context: Context,
) -> None:
    """Функция score динамически подхватывает новые веса после update_weights."""
    r001 = reports_map["r001"]
    cluster = Cluster(
        id="c_test_dyn",
        category=r001.category,
        centroid=r001.location,
        report_ids=["r001"],
        first_reported_at=r001.created_at,
        last_reported_at=r001.created_at,
    )
    score_before = priority.score(cluster, [r001], [], base_context)

    modified_w = {
        "HZ": 0.01,
        "DM": 0.50,
        "AG": 0.01,
        "SP": 0.01,
        "RC": 0.01,
        "WX": 0.01,
        "VF": 0.40,
        "EX": 0.05,
    }
    priority.update_weights(modified_w)

    score_after = priority.score(cluster, [r001], [], base_context)
    hz_factor = next(f for f in score_after.factors if f.code == "HZ")
    assert hz_factor.weight == 0.01
    dm_factor = next(f for f in score_after.factors if f.code == "DM")
    assert dm_factor.weight == 0.50
    assert score_before.score != score_after.score
