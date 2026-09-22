"""Роуты блока B0. Контракт: docs/contracts/B0_*.md."""

from fastapi import APIRouter

router = APIRouter(prefix="/clusters", tags=["clusters"])
