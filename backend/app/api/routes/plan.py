"""Роуты блока B6. Контракт: docs/contracts/B6_dispatch.md."""

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import CurrentUser, get_current_user, require_roles
from app.blocks import dispatch
from app.contracts.models import Crew, Plan

log = logging.getLogger(__name__)

router = APIRouter(tags=["plan"], dependencies=[Depends(get_current_user)])


class PlanCreate(BaseModel):
    day: date


@router.post("/plan", response_model=Plan)
def create_plan(body: PlanCreate) -> Plan:
    try:
        return dispatch.create_plan(body.day)
    except NotImplementedError as exc:
        log.warning("B6: зависимость плана ещё не реализована", exc_info=True)
        raise HTTPException(
            status_code=503, detail="Зависимость блока ещё не реализована"
        ) from exc


@router.get("/plan/current", response_model=Plan)
def read_current_plan() -> Plan:
    plan = dispatch.get_current_plan()
    if plan is None:
        raise HTTPException(status_code=404, detail="Действующий план не найден")
    return plan


@router.get("/plan/draft", response_model=Plan)
def read_draft_plan() -> Plan:
    plan = dispatch.get_draft_plan()
    if plan is None:
        raise HTTPException(status_code=404, detail="Черновик не найден")
    return plan


@router.get("/plan/{plan_id}", response_model=Plan)
def read_plan(plan_id: str) -> Plan:
    plan = dispatch.get_plan(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="План не найден")
    return plan


@router.post(
    "/plan/{plan_id}/approve",
    response_model=Plan,
    dependencies=[Depends(require_roles("supervisor"))],
)
def approve_plan(plan_id: str, current_user: CurrentUser) -> Plan:
    plan = dispatch.approve_plan(plan_id, current_user.email)
    if plan is None:
        raise HTTPException(status_code=404, detail="План не найден")
    return plan


@router.get("/crews", response_model=list[Crew])
def read_crews() -> list[Crew]:
    return dispatch.get_crews()
