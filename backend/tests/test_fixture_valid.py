"""Общий fixture обязан проходить через модели контрактов — на нём стоят тесты всех блоков."""

import json
from pathlib import Path

from app.contracts.models import (
    CATEGORIES,
    SKILLS,
    Crew,
    Event,
    InfraObject,
    Report,
    Weather,
)

FIXTURE = Path(__file__).resolve().parent.parent / "app" / "fixtures" / "demo_city.json"


def load() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_fixture_matches_contract_models() -> None:
    data = load()
    reports = [Report(**r) for r in data["reports"]]
    crews = [Crew(**c) for c in data["crews"]]
    [InfraObject(**i) for i in data["infrastructure"]]
    [Event(**e) for e in data["events"]]
    [Weather(**w) for w in data["weather"].values()]

    assert {r.category for r in reports} <= set(CATEGORIES)
    assert {s for c in crews for s in c.skills} <= set(SKILLS)
    assert len({r.id for r in reports}) == len(reports)


def test_fixture_expectations_are_consistent() -> None:
    data = load()
    expect = data["expect"]
    ids = {r["id"] for r in data["reports"]}
    open_reports = [r for r in data["reports"] if r["status"] == "open"]

    assert len(open_reports) == expect["open_reports"]
    for key in ("dup_trio", "not_dup", "site_batch", "top2_priority_reports"):
        assert set(expect[key]) <= ids
    assert expect["suspicious_report"] in ids
