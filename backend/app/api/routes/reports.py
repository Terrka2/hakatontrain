"""Роуты блока B1. Контракт: docs/contracts/B1_ingest.md."""

import hashlib
import logging
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Protocol

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.api.deps import require_roles
from app.blocks import ingest
from app.blocks.operator import operator_run
from app.contracts.models import GeoPoint, Report, Verification
from app.db import get_repository

log = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])


class ImportResponse(BaseModel):
    imported: int
    rejected: list[dict[str, Any]]


class ReportCreateRequest(BaseModel):
    category: str
    text: str
    lat: float
    lon: float
    address: str | None = None
    photo_url: str | None = None


class ReportRepository(Protocol):
    def list_reports(
        self, *, status: str | None = None, category: str | None = None
    ) -> list[Report]: ...
    def upsert_reports(self, reports: list[Report]) -> int: ...
    def confirm_report(self, report_id: str) -> Report: ...


RepoDep = Annotated[ReportRepository, Depends(get_repository)]


@router.post(
    "/import",
    response_model=ImportResponse,
    dependencies=[Depends(require_roles("supervisor"))],
)
async def import_reports(
    repo: RepoDep,
    file: UploadFile = File(...),
) -> ImportResponse:
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

    repo.upsert_reports(result.reports)

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
    repo: RepoDep,
    status: str | None = None,
    category: str | None = None,
    bbox: str | None = None,
) -> list[Report]:
    """Получение списка обращений с фильтрацией по status, category и bbox."""
    reports = repo.list_reports(status=status, category=category)

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
def create_report(
    req: ReportCreateRequest,
    repo: RepoDep,
) -> Report:
    """Создание обращения жителем: сразу verification.status='unverified'."""
    now = datetime.now(UTC)
    text_str = req.text.strip()
    report_id = hashlib.md5(f"{text_str}{req.lat}{req.lon}{now}".encode()).hexdigest()[
        :12
    ]

    # Валидация категории через нормализацию
    try:
        norm = ingest.normalize(
            {
                "id": report_id,
                "category": req.category,
                "text": text_str,
                "lat": req.lat,
                "lon": req.lon,
                "address": req.address,
                "photo_url": req.photo_url,
                "created_at": now.isoformat(),
            }
        )
        cat = norm.category
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    report = Report(
        id=report_id,
        source="citizen",
        category=cat,
        text=text_str,
        location=GeoPoint(lat=req.lat, lon=req.lon),
        address=req.address.strip() if req.address else None,
        photo_url=req.photo_url.strip() if req.photo_url else None,
        created_at=now,
        status="open",
        verification=Verification(status="unverified", reasons=[], confidence=0.0),
        confirmations=0,
    )

    repo.upsert_reports([report])

    try:
        operator_run(trigger="new_report", now=datetime.now(UTC))
    except Exception:  # noqa: BLE001
        log.warning("operator_run trigger 'new_report' failed", exc_info=True)

    return report


@router.post("/{id}/confirm", response_model=Report)
def confirm_report(
    id: str,
    repo: RepoDep,
) -> Report:
    """Подтверждение обращения: confirmations += 1."""
    try:
        report = repo.confirm_report(id)
        if report is None:
            raise HTTPException(status_code=404, detail="Report not found")
        return report
    except KeyError as e:
        raise HTTPException(status_code=404, detail="Report not found") from e
    except HTTPException:
        raise
    except Exception as e:
        log.error("confirm_report failed: %s", e)
        raise HTTPException(status_code=404, detail="Report not found") from e
