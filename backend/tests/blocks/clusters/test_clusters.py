import json
from datetime import timedelta
from pathlib import Path

import pytest

from app.blocks.clusters import build_clusters
from app.contracts.models import Report


def reports() -> list[Report]:
    data = json.loads(
        (Path(__file__).resolve().parents[3] / "app/fixtures/demo_city.json").read_text(
            encoding="utf-8"
        )
    )
    return [Report.model_validate(row) for row in data["reports"]]


def test_fixture_clusters_and_links() -> None:
    rows = reports()
    groups = build_clusters(rows)
    assert len(groups) == 13
    trio = next(c for c in groups if c.id == "cl_r001")
    assert trio.report_ids == ["r001", "r002", "r003"]
    assert len(trio.links) == 3 and all(link.distance_m < 50 for link in trio.links)
    assert all("r016" not in c.report_ids for c in groups)
    assert next(c for c in groups if "r004" in c.report_ids).id != trio.id
    assert (
        len(
            [
                c
                for c in groups
                if any(i in c.report_ids for i in ["r007", "r008", "r009", "r010"])
            ]
        )
        == 4
    )
    assert groups == build_clusters(list(reversed(rows)))


def test_similarity_window_and_boundaries() -> None:
    first = reports()[0]
    second = first.model_copy(deep=True, update={"id": "r002", "text": " OTHER text! "})
    second.location.lat += 0.00072
    assert len(build_clusters([first, second], lambda a, b: 0.9)) == 1
    assert len(build_clusters([first, second], lambda a, b: 0.1)) == 2
    second.created_at += timedelta(days=31)
    assert len(build_clusters([first, second], lambda a, b: 1)) == 2
    assert build_clusters([]) == []
    assert build_clusters([first])[0].report_ids == [first.id]
    with pytest.raises(ValueError):
        build_clusters([first, first])
