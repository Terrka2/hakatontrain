"""Роуты блока B6. Контракт: docs/contracts/B6_*.md."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.blocks.operator import get_plan, get_runs
from app.contracts.models import Plan

router = APIRouter(
    prefix="/plan", tags=["plan"], dependencies=[Depends(get_current_user)]
)


@router.get("/draft", response_model=Plan)
def read_draft() -> Plan:
    for run in get_runs(100):
        if run.plan_id and (plan := get_plan(run.plan_id)):
            return plan
    raise HTTPException(status_code=404, detail="Draft not found")


@router.get("/{plan_id}", response_model=Plan)
def read_plan(plan_id: str) -> Plan:
    plan = get_plan(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan
