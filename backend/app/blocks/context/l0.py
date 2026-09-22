"""L0: детерминированный контекст из demo_city.json."""

import json
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.contracts.models import Context, Decision, GeoPoint, InfraObject, Job, Weather
from app.core.config import settings

_FIXTURE_PATH = Path(__file__).resolve().parents[2] / "fixtures" / "demo_city.json"
_RULES_PATH = Path(__file__).resolve().parent / "weather_rules.yaml"
_scen: str | None = None


def set_scenario(s: str) -> None:
    global _scen
    _scen = s


def reset_scenario() -> None:
    global _scen
    _scen = None


@lru_cache(maxsize=1)
def _data() -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, str]]:
    with _FIXTURE_PATH.open("r", encoding="utf-8") as f:
        fxt = json.load(f)
    with _RULES_PATH.open("r", encoding="utf-8") as f:
        rules = (yaml.safe_load(f) or {}).get("rules", [])
    rep_map = {
        r["id"]: r["category"]
        for r in fxt.get("reports", [])
        if "id" in r and "category" in r
    }
    return fxt, rules, rep_map


def _category(job: Job, rep_map: dict[str, str]) -> str:
    if custom := job.__dict__.get("category"):
        return str(custom)
    if job.skill in (
        "tree",
        "pothole",
        "manhole",
        "streetlight",
        "garbage",
        "public_space",
        "water_leak",
        "traffic_sign",
    ):
        return job.skill
    if job.skill == "green":
        return "tree"
    for cid in job.cluster_ids:
        c = rep_map.get(cid, cid.lower())
        if "pothole" in c:
            return "pothole"
        if "tree" in c and "street" not in c:
            return "tree"
    j = job.id.lower()
    return (
        "pothole"
        if "pothole" in j
        else ("tree" if "tree" in j and "street" not in j else "other")
    )


def get_weather(point: GeoPoint, at: datetime) -> Weather | None:
    _ = point
    fxt, _, _ = _data()
    key = (_scen or settings.WEATHER).split(":")[-1]
    it = fxt.get("weather", {}).get(key) or fxt.get("weather", {}).get("clear", {})
    if not it:
        return None
    return Weather(
        at=at,
        precipitation_mm=float(it.get("precipitation_mm", 0.0)),
        wind_ms=float(it.get("wind_ms", 0.0)),
        temp_c=float(it.get("temp_c", 0.0)),
        source="fixture",
    )


def build_context(now: datetime) -> Context:
    fxt, _, _ = _data()
    infra = [InfraObject(**o) for o in fxt.get("infrastructure", [])]
    return Context(
        now=now,
        weather=get_weather(GeoPoint(lat=47.018, lon=28.842), now),
        events=[],
        infrastructure=infra,
    )


def apply_weather_rules(
    jobs: list[Job], weather: Weather | None
) -> tuple[list[Job], list[Decision]]:
    if weather is None:
        return list(jobs), []
    _, rules, rep_map = _data()
    kept, decisions = [], []
    for job in jobs:
        cat, curr, deferred = _category(job, rep_map), job, False
        for r in rules:
            c, act, tgt, t = r["condition"], r["action"], r.get("target", {}), r["type"]
            if getattr(weather, c["field"], 0.0) < c["value"]:
                continue
            if (
                t == "defer"
                and cat == tgt.get("category")
                and (not tgt.get("skill") or curr.skill == tgt.get("skill"))
            ):
                decisions.append(
                    Decision(
                        kind="defer",
                        subject_id=curr.id,
                        reason=act["reason"],
                        by="rule",
                    )
                )
                deferred = True
                break
            if t == "boost" and cat == tgt.get("category"):
                p = min(
                    act.get("max_priority", 100),
                    curr.priority + act.get("delta_priority", 20),
                )
                if p != curr.priority:
                    curr = curr.model_copy(update={"priority": p})
                    decisions.append(
                        Decision(
                            kind="boost",
                            subject_id=curr.id,
                            reason=act["reason"],
                            by="rule",
                        )
                    )
            elif t == "slow" and cat not in tgt.get("exclude_categories", []):
                s = int(round(curr.service_min * act.get("factor", 1.3)))
                if s != curr.service_min:
                    curr = curr.model_copy(update={"service_min": s})
                    decisions.append(
                        Decision(
                            kind="param",
                            subject_id=curr.id,
                            reason=act["reason"],
                            by="rule",
                        )
                    )
        if not deferred:
            kept.append(curr)
    return kept, decisions
