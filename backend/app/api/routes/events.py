"""Роуты блока X1. Контракт: docs/contracts/X1_events.md."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import require_roles
from app.blocks.events import get_events, l0
from app.contracts.models import Event
from app.core.config import settings


def require_optional_blocks() -> None:
    if settings.OPTIONAL_BLOCKS != "on":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Блок мероприятий отключён (OPTIONAL_BLOCKS=off)",
        )


router = APIRouter(
    prefix="/events",
    tags=["events"],
    dependencies=[Depends(require_optional_blocks)],
)


@router.get(
    "",
    response_model=list[Event],
    dependencies=[Depends(require_roles("supervisor", "operator", "crew", "citizen"))],
)
def list_events(
    from_: datetime | None = Query(None, alias="from"),
    to_: datetime | None = Query(None, alias="to"),
) -> list[Event]:
    start = from_ or datetime(2000, 1, 1, tzinfo=UTC)
    end = to_ or datetime(2100, 1, 1, tzinfo=UTC)
    return get_events(start, end)


@router.post(
    "",
    response_model=Event,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("supervisor"))],
)
def create_event(event: Event) -> Event:
    return l0.add_event(event)
