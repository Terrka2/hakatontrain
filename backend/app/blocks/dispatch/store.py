"""L0: план и бригады хранятся в памяти процесса, отдельно от run-хранилища блока B0.

Бригады — только чтение из demo_city.json (без своих данных, `expect` не трогаем).
"""

import json
from datetime import datetime
from pathlib import Path

from app.contracts.models import Crew, Plan

FIXTURE_PATH = Path(__file__).resolve().parents[2] / "fixtures" / "demo_city.json"

_plans: dict[str, Plan] = {}
_order: list[str] = []  # порядок сохранения планов (последний — самый свежий)
_current_id: str | None = None  # id действующего (approved) плана


def reset() -> None:
    """Сброс состояния хранилища (для тестов)."""
    global _current_id
    _plans.clear()
    _order.clear()
    _current_id = None


def _fixture() -> dict:
    with FIXTURE_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def load_crews() -> list[Crew]:
    """Бригады из demo_city.json."""
    return [Crew.model_validate(c) for c in _fixture().get("crews", [])]


def fixture_now() -> datetime:
    """Время `now` из demo_city.json (для построения контекста по умолчанию)."""
    return datetime.fromisoformat(_fixture()["now"])


def record_plan(plan: Plan) -> Plan:
    """Сохраняет план (новый черновик или результат replan) в хранилище."""
    stored = plan.model_copy(update={"status": "draft"})
    _plans[stored.id] = stored
    _order.append(stored.id)
    return stored.model_copy(deep=True)


def get(plan_id: str) -> Plan | None:
    plan = _plans.get(plan_id)
    return plan.model_copy(deep=True) if plan is not None else None


def get_draft() -> Plan | None:
    """Последний сохранённый план, независимо от текущего статуса."""
    if not _order:
        return None
    plan = _plans.get(_order[-1])
    return plan.model_copy(deep=True) if plan is not None else None


def get_current() -> Plan | None:
    """Действующий (approved) план."""
    if _current_id is None:
        return None
    plan = _plans.get(_current_id)
    return plan.model_copy(deep=True) if plan is not None else None


def approve(plan_id: str, approved_by: str) -> Plan | None:
    """Утверждает план: предыдущий действующий переходит в superseded."""
    global _current_id
    plan = _plans.get(plan_id)
    if plan is None:
        return None
    if _current_id is not None and _current_id != plan_id and _current_id in _plans:
        previous = _plans[_current_id]
        _plans[_current_id] = previous.model_copy(update={"status": "superseded"})
    approved_plan = plan.model_copy(
        update={"status": "approved", "approved_by": approved_by}
    )
    _plans[plan_id] = approved_plan
    _current_id = plan_id
    return approved_plan.model_copy(deep=True)
