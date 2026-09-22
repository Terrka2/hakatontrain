"""Роуты блока <ID>. Только вызывают порт блока и отдают модели контрактов. Логики здесь нет."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import CurrentUser, require_roles
from app.blocks import example  # порт соседа/своего блока — только через __init__
from app.contracts.models import Priority

router = APIRouter(prefix="/example", tags=["example"])  # файл и prefix уже созданы C0 — не переименовывать


@router.get("/{cluster_id}", response_model=Priority)
def read_priority(cluster_id: str, current_user: CurrentUser) -> Priority:
    result = example.get_priority(cluster_id)
    if result is None:
        raise HTTPException(status_code=404, detail="cluster not found")
    return result


@router.post("/{cluster_id}/review", dependencies=[Depends(require_roles("supervisor"))])
def review(cluster_id: str, decision: str) -> dict[str, str]:
    example.review(cluster_id, decision)
    return {"status": "ok"}
