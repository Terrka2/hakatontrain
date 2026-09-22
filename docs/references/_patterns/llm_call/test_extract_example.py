"""Тесты LLM-уровня без сети: complete_json подменяется."""

import pytest

from app.blocks.extractor import l1
from app.blocks.extractor.l1 import Extracted


def test_extract_uses_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(l1, "complete_json", lambda *a, **k: Extracted(injured=True))
    assert l1.extract("человек упал в люк").injured is True


def test_extract_returns_none_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(l1, "complete_json", lambda *a, **k: None)
    assert l1.extract("что угодно") is None
