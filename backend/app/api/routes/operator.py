"""Роуты блока B0. Контракт: docs/contracts/B0_*.md."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_current_user, require_roles
from app.blocks import operator
from app.contracts.models import OperatorRun, OperatorRunRequest

router = APIRouter(
    prefix="/operator", tags=["operator"], dependencies=[Depends(get_current_user)]
)


@router.get("/runs", response_model=list[OperatorRun])
def read_runs(limit: Annotated[int, Query(ge=1, le=100)] = 20) -> list[OperatorRun]:
    return operator.get_runs(limit)


@router.post(
    "/run",
    response_model=OperatorRun,
    dependencies=[Depends(require_roles("supervisor"))],
)
def run_operator(body: OperatorRunRequest) -> OperatorRun:
    try:
        return operator.operator_run(body.trigger, operator.fixture_now())
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=503, detail="Operator dependencies are not ready"
        ) from exc
