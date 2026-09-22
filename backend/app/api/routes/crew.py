"""Роуты блока B8. Контракт: docs/contracts/B8_fieldwork.md."""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import ValidationError

from app.api.deps import require_roles
from app.blocks.fieldwork import apply_update, get_crew_route, progress
from app.contracts.models import CrewRoute, JobUpdate, RouteStop
from app.db import Repository, get_repository
from app.models import User

router = APIRouter(prefix="/crew", tags=["crew"])
CrewUser = Annotated[User, Depends(require_roles("crew"))]
UPLOAD_DIR = Path("uploads")


@router.get("/me/route", response_model=CrewRoute)
def get_my_route(current_user: CrewUser) -> CrewRoute:
    cid = current_user.crew_id
    if not cid or not (route := get_crew_route(cid)):
        raise HTTPException(404, "Маршрут не найден или план не утверждён")
    return route


@router.post("/jobs/{job_id}/status", response_model=RouteStop)
async def update_job_status(
    job_id: str,
    request: Request,
    current_user: CrewUser,
    repo: Repository = Depends(get_repository),
) -> RouteStop:
    content_type = request.headers.get("content-type", "")
    photo_url: str | None = None
    payload: dict[str, Any]

    if "multipart/form-data" in content_type:
        form = await request.form()
        for v in form.values():
            filename = getattr(v, "filename", None)
            if filename and hasattr(v, "read"):
                ext = Path(str(filename)).suffix or ".jpg"
                fname = f"{uuid.uuid4()}{ext}"
                UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
                dest = UPLOAD_DIR / fname
                dest.write_bytes(await v.read())
                photo_url = f"uploads/{fname}"
                break

        at_val = form.get("at")
        at_dt = datetime.fromisoformat(str(at_val)) if at_val else datetime.now()

        loc_data: Any = None
        if "location" in form:
            loc_val = form.get("location")
            if isinstance(loc_val, str):
                try:
                    loc_data = json.loads(loc_val)
                except Exception:
                    pass
            elif isinstance(loc_val, dict):
                loc_data = loc_val
        if loc_data is None and "lat" in form and "lon" in form:
            try:
                loc_data = {
                    "lat": float(str(form.get("lat"))),
                    "lon": float(str(form.get("lon"))),
                }
            except Exception:
                pass

        payload = {
            "job_id": str(form.get("job_id", job_id)),
            "crew_id": str(form.get("crew_id", current_user.crew_id or "")),
            "status": form.get("status"),
            "at": at_dt,
            "photo_url": photo_url or form.get("photo_url"),
            "reason": form.get("reason"),
            "needs_skill": form.get("needs_skill"),
            "note": form.get("note"),
        }
        if loc_data is not None:
            payload["location"] = loc_data
    else:
        payload = await request.json()

    try:
        update = JobUpdate.model_validate(payload)
    except ValidationError as e:
        raise HTTPException(422, detail=e.errors()) from e

    if job_id != update.job_id:
        raise HTTPException(400, "job_id в URL не совпадает с телом")
    cid = current_user.crew_id
    if not current_user.is_superuser and cid and cid != update.crew_id:
        raise HTTPException(403, "Чужая бригада")
    return apply_update(update, repo=repo)


@router.get(
    "/progress",
    response_model=dict[str, dict[str, int]],
    dependencies=[Depends(require_roles("supervisor"))],
)
def get_progress(plan_id: str = "plan_demo") -> dict[str, dict[str, int]]:
    if not (res := progress(plan_id)):
        raise HTTPException(404, f"План {plan_id} не найден")
    return res
