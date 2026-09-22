"""Роуты блока L2. Контракт: docs/contracts/L2_*.md."""

from fastapi import APIRouter

router = APIRouter(prefix="/assistant", tags=["assistant"])
