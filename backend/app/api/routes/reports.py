"""Роуты блока B1. Контракт: docs/contracts/B1_ingest.md."""

import logging
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.api.deps import require_roles
from app.blocks import ingest
from app.blocks.ingest.l0 import get_store
from app.blocks.operator import operator_run
from app.contracts.models import Report, Verification

log = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])


class ImportResponse(BaseModel):
    imported: int
    rejected: list[dict[str, Any]]


@router.post(
    "/import",
    response_model=ImportResponse,
    dependencies=[Depends(require_roles("supervisor"))],
)
async def import_reports(file: UploadFile = File(...)) -> ImportResponse:
    """Импорт обращений из файла (CSV/JSON). Доступно только supervisor."""
    suffix = Path(file.filename or "data.json").suffix
    content = await file.read()

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        result = ingest.parse_file(tmp_path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

    store = get_store()
    for report in result.reports:
        store[report.id] = report

    try:
        operator_run(trigger="import", now=datetime.now(UTC))
    except Exception:  # noqa: BLE001
        log.warning("operator_run trigger 'import' failed", exc_info=True)

    return ImportResponse(
        imported=len(result.reports),
        rejected=result.rejected,
    )


@router.get("", response_model=list[Report])
@router.get("/", response_model=list[Report], include_in_schema=False)
def read_reports(
    status: str | None = None,
    category: str | None = None,
    bbox: str | None = None,
) -> list[Report]:
    """Получение списка обращений с фильтрацией по status, category и bbox."""
    reports = list(get_store().values())

    if status:
        reports = [r for r in reports if r.status == status]

    if category:
        reports = [r for r in reports if r.category == category]

    if bbox:
        try:
            parts = [float(x.strip()) for x in bbox.split(",")]
            if len(parts) == 4:
                min_lon, min_lat, max_lon, max_lat = parts
                reports = [
                    r
                    for r in reports
                    if min_lat <= r.location.lat <= max_lat
                    and min_lon <= r.location.lon <= max_lon
                ]
        except ValueError, TypeError:
            pass

    return reports


@router.post("", response_model=Report)
@router.post("/", response_model=Report, include_in_schema=False)
def create_report(report: Report) -> Report:
    """Создание обращения жителем: сразу verification.status='unverified'."""
    report.verification = Verification(status="unverified", reasons=[], confidence=0.0)
    store = get_store()
    store[report.id] = report

    try:
        operator_run(trigger="new_report", now=datetime.now(UTC))
    except Exception:  # noqa: BLE001
        log.warning("operator_run trigger 'new_report' failed", exc_info=True)

    return report


@router.post("/{id}/confirm", response_model=Report)
def confirm_report(id: str) -> Report:
    """Подтверждение обращения: confirmations += 1."""
    store = get_store()
    if id not in store:
        raise HTTPException(status_code=404, detail="Report not found")

    report = store[id]
    report.confirmations += 1
    return report
