"""Роуты блока B5 (context). Контракт: docs/contracts/B5_context.md."""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import CurrentUser, require_roles
from app.blocks import context
from app.contracts.models import Context

router = APIRouter(prefix="/context", tags=["context"])


class WeatherScenarioPayload(BaseModel):
    scenario: str


@router.get("", response_model=Context)
def read_context(_current_user: CurrentUser) -> Context:
    return context.build_context(now=datetime.now(UTC))


@router.put("/weather-scenario", dependencies=[Depends(require_roles("supervisor"))])
def update_weather_scenario(payload: WeatherScenarioPayload) -> dict[str, Any]:
    context.set_scenario(payload.scenario)
    try:
        from app.blocks import operator

        operator.operator_run(trigger="weather_changed", now=datetime.now(UTC))
    except Exception:  # noqa: BLE001
        pass
    return {"status": "ok", "scenario": payload.scenario}
