"""Роуты блока D2. Контракт: docs/contracts/D2_search.md. Только вызывают порт блока, логики здесь нет."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from app.api.deps import require_roles
from app.blocks import search
from app.blocks.search import Hit

router = APIRouter(prefix="/search", tags=["search"])


@router.get(
    "",
    response_model=list[Hit],
    dependencies=[Depends(require_roles("supervisor", "crew"))],
)
def read_search(
    q: str = Query(..., min_length=1),
    k: int = Query(default=5, ge=1, le=50),
    kind: Annotated[Literal["report", "event"] | None, Query()] = None,
) -> list[Hit]:
    return search.search(q, k, kind)
