"""Роуты блока X1. Контракт: docs/contracts/X1_*.md."""

from fastapi import APIRouter

router = APIRouter(prefix="/events", tags=["events"])
