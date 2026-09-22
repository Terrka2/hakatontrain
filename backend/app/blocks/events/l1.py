"""Уровень L1 блока X1: работа с мероприятиями через репозиторий D1."""

from datetime import datetime

from app.contracts import models
from app.db import Repository, get_repository


def get_events(
    start: datetime, end: datetime, repo: Repository | None = None
) -> list[models.Event]:
    r = repo or get_repository()
    return r.list_events(start, end)


def add_event(event: models.Event, repo: Repository | None = None) -> models.Event:
    r = repo or get_repository()
    return r.add_event(event)
