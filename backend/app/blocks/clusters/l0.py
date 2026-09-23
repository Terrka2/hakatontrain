"""Deterministic union-find using the B3 distance, time and text rules."""

import re
from collections.abc import Callable
from itertools import combinations

from app.blocks.geo import centroid, haversine_m
from app.contracts.models import Cluster, DupLink, Report


def _jaccard(a: str, b: str) -> float:
    left, right = (set(re.findall(r"\w+", text.casefold())) for text in (a, b))
    return len(left & right) / len(left | right) if left | right else 0.0


def build_clusters(
    reports: list[Report], similarity: Callable[[str, str], float] | None = None
) -> list[Cluster]:
    from . import DUP_RADIUS_M, DUP_SURE_RADIUS_M, DUP_TEXT_SIM, DUP_WINDOW_DAYS

    if len({r.id for r in reports}) != len(reports):
        raise ValueError("Duplicate report ids")
    rows = sorted((r for r in reports if r.status == "open"), key=lambda r: r.id)
    parents = {r.id: r.id for r in rows}
    links: list[DupLink] = []

    def root(key: str) -> str:
        while parents[key] != key:
            parents[key] = parents[parents[key]]
            key = parents[key]
        return key

    for a, b in combinations(rows, 2):
        if (
            a.category != b.category
            or abs((a.created_at - b.created_at).total_seconds())
            > DUP_WINDOW_DAYS * 86400
        ):
            continue
        distance = haversine_m(a.location, b.location)
        if distance > DUP_RADIUS_M:
            continue
        sim = (similarity or _jaccard)(a.text, b.text)
        if distance <= DUP_SURE_RADIUS_M or sim >= DUP_TEXT_SIM:
            parents[root(b.id)] = root(a.id)
            links.append(DupLink(a=a.id, b=b.id, distance_m=distance, text_sim=sim))
    groups: dict[str, list[Report]] = {}
    for row in rows:
        groups.setdefault(root(row.id), []).append(row)
    result = []
    for group in groups.values():
        ids = [r.id for r in group]
        result.append(
            Cluster(
                id="cl_" + min(ids),
                category=group[0].category,
                centroid=centroid([r.location for r in group]),
                report_ids=ids,
                links=[link for link in links if link.a in ids and link.b in ids],
                first_reported_at=min(r.created_at for r in group),
                last_reported_at=max(r.created_at for r in group),
            )
        )
    return sorted(result, key=lambda c: c.id)
