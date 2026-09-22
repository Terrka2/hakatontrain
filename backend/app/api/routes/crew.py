"""Роуты блока B8. Контракт: docs/contracts/B8_fieldwork.md."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import require_roles
from app.blocks.fieldwork import apply_update, get_crew_route, progress
from app.contracts.models import CrewRoute, JobUpdate, RouteStop
from app.models import User

router = APIRouter(prefix="/crew", tags=["crew"])
CrewUser = Annotated[User, Depends(require_roles("crew"))]


@router.get("/me/route", response_model=CrewRoute)
def get_my_route(current_user: CrewUser) -> CrewRoute:
    cid = current_user.crew_id
    if not cid or not (route := get_crew_route(cid)):
        raise HTTPException(404, "Маршрут не найден или план не утверждён")
    return route


@router.post("/jobs/{job_id}/status", response_model=RouteStop)
def update_job_status(
    job_id: str, update: JobUpdate, current_user: CrewUser
) -> RouteStop:
    if job_id != update.job_id:
        raise HTTPException(400, "job_id в URL не совпадает с телом")
    cid = current_user.crew_id
    if not current_user.is_superuser and cid and cid != update.crew_id:
        raise HTTPException(403, "Чужая бригада")
    return apply_update(update)


@router.get(
    "/progress",
    response_model=dict[str, dict[str, int]],
    dependencies=[Depends(require_roles("supervisor"))],
)
def get_progress(plan_id: str = "plan_demo") -> dict[str, dict[str, int]]:
    if not (res := progress(plan_id)):
        raise HTTPException(404, f"План {plan_id} не найден")
    return res
