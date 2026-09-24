"""B3 L0 contract, boundary and deterministic clustering checks."""

import json
import socket
from datetime import UTC, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from app.blocks import clusters
from app.blocks.clusters import build_clusters, l0
from app.contracts.models import Report


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def blocked(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("B3 must not access the network")

    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)


@pytest.fixture
def data() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[3] / "app/fixtures/demo_city.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def rows(data: dict[str, Any]) -> list[Report]:
    return [Report.model_validate(row) for row in data["reports"]]


def pair(rows: list[Report]) -> list[Report]:
    first = rows[0].model_copy(deep=True)
    second = first.model_copy(deep=True, update={"id": "pair-second"})
    second.location.lat += 0.00072
    return [first, second]


def test_fixture_count(data: dict[str, Any], rows: list[Report]) -> None:
    assert len(build_clusters(rows)) == data["expect"]["clusters"]


def test_trio_links(data: dict[str, Any], rows: list[Report]) -> None:
    trio_ids = sorted(data["expect"]["dup_trio"])
    trio = next(c for c in build_clusters(rows) if c.id == "cl_" + trio_ids[0])
    assert trio.report_ids == trio_ids
    assert {(link.a, link.b) for link in trio.links} == {
        (trio_ids[0], trio_ids[1]),
        (trio_ids[0], trio_ids[2]),
        (trio_ids[1], trio_ids[2]),
    }
    assert all(0 <= link.distance_m < 50 for link in trio.links)
    by_id = {r.id: r for r in rows}
    for link in trio.links:
        assert link.text_sim == l0._jaccard(by_id[link.a].text, by_id[link.b].text)


def test_categories_stay_separate(rows: list[Report]) -> None:
    membership = {rid: c.id for c in build_clusters(rows) for rid in c.report_ids}
    assert membership["r001"] != membership["r004"]


def test_separate_potholes(rows: list[Report]) -> None:
    membership = {rid: c.id for c in build_clusters(rows) for rid in c.report_ids}
    assert len({membership[rid] for rid in ("r007", "r008", "r009", "r010")}) == 4


@pytest.mark.parametrize(("similarity", "count"), [(0.9, 1), (0.1, 2)])
def test_eighty_metre_pair(rows: list[Report], similarity: float, count: int) -> None:
    assert len(build_clusters(pair(rows), lambda a, b: similarity)) == count


def test_only_open(rows: list[Report]) -> None:
    expected = {r.id for r in rows if r.status == "open"}
    assert {rid for c in build_clusters(rows) for rid in c.report_ids} == expected
    assert "r016" not in expected
    for status in ("in_progress", "resolved", "rejected"):
        assert build_clusters([rows[0].model_copy(update={"status": status})]) == []


def test_deterministic_and_input_unchanged(rows: list[Report]) -> None:
    original = [r.model_dump(mode="json") for r in rows]
    expected = build_clusters(rows)
    assert build_clusters(rows) == expected
    assert build_clusters(list(reversed(rows))) == expected
    assert build_clusters(rows[5:] + rows[:5]) == expected
    assert [r.model_dump(mode="json") for r in rows] == original


@pytest.mark.parametrize(
    ("distance", "sim", "count"),
    [
        (0, 0, 1),
        (50, 0, 1),
        (50.001, 0, 2),
        (80, 0.4999, 2),
        (80, 0.5, 1),
        (100, 0.5, 1),
        (100.001, 1, 2),
    ],
)
def test_distance_thresholds(
    rows: list[Report],
    monkeypatch: pytest.MonkeyPatch,
    distance: float,
    sim: float,
    count: int,
) -> None:
    monkeypatch.setattr(l0, "haversine_m", lambda a, b: distance)
    assert len(build_clusters(pair(rows), lambda a, b: sim)) == count


@pytest.mark.parametrize(
    ("days", "seconds", "count"),
    [
        (30, 0, 1),
        (30, 1, 2),
        (-30, 0, 1),
        (-30, -1, 2),
    ],
)
def test_time_window(rows: list[Report], days: int, seconds: int, count: int) -> None:
    first, second = pair(rows)
    second.created_at = first.created_at + timedelta(days=days, seconds=seconds)
    assert len(build_clusters([first, second], lambda a, b: 1)) == count


def test_timezone_midnight_and_cluster_metadata(rows: list[Report]) -> None:
    first, second = pair(rows)
    first.created_at = first.created_at.replace(hour=23, minute=59)
    second.created_at = (first.created_at + timedelta(minutes=2)).astimezone(UTC)
    result = build_clusters([first, second], lambda a, b: 1)[0]
    assert result.first_reported_at == first.created_at
    assert result.last_reported_at == second.created_at
    assert result.centroid.lat == pytest.approx(
        (first.location.lat + second.location.lat) / 2
    )
    assert result.centroid.lon == pytest.approx(first.location.lon)
    assert result.category == first.category and result.status == "open"
    shifted = [
        r.model_copy(
            update={
                "created_at": r.created_at.astimezone(timezone(timedelta(hours=-5)))
            }
        )
        for r in (first, second)
    ]
    assert build_clusters(shifted, lambda a, b: 1) == [result]


def test_empty_single_optional_and_duplicates(rows: list[Report]) -> None:
    assert build_clusters([]) == []
    row = rows[0].model_copy(
        deep=True,
        update={
            "address": None,
            "photo_url": None,
            "lang": None,
            "extracted": None,
            "verification": None,
            "cluster_id": None,
        },
    )
    single = build_clusters([row])[0]
    assert single.id == "cl_" + row.id and single.report_ids == [row.id]
    assert single.centroid == row.location and single.links == []
    single.centroid.lat += 1
    assert row.location == rows[0].location
    with pytest.raises(ValueError, match="Duplicate report ids"):
        build_clusters([row, row.model_copy()])


def test_jaccard_normalizes_punctuation(rows: list[Report]) -> None:
    first, second = pair(rows)
    second.text = "  " + first.text.upper().replace(" ", "_!!! ") + "  "
    cluster = build_clusters([first, second])[0]
    assert cluster.report_ids == sorted([first.id, second.id])
    assert cluster.links[0].text_sim == 1


def test_jaccard_empty_text(rows: list[Report]) -> None:
    first, second = pair(rows)
    first.text, second.text = "", " !!! "
    assert len(build_clusters([first, second])) == 2
    second.location = first.location.model_copy()
    result = build_clusters([first, second])[0]
    assert result.links[0].text_sim == 0


def test_transitive_union_and_all_pair_explanations(rows: list[Report]) -> None:
    first = rows[0].model_copy(deep=True)
    second = first.model_copy(deep=True, update={"id": "chain-b"})
    third = first.model_copy(deep=True, update={"id": "chain-c"})
    second.location.lat += 0.00072
    third.location.lat += 0.00144
    result = build_clusters([third, first, second], lambda a, b: 0.75)
    assert len(result) == 1
    assert result[0].report_ids == sorted([first.id, second.id, third.id])
    assert result[0].id == "cl_" + min(first.id, second.id, third.id)
    assert len(result[0].links) == 2
    assert all(link.text_sim == 0.75 for link in result[0].links)


def test_similarity_is_recorded_even_inside_sure_radius(rows: list[Report]) -> None:
    first, second = pair(rows)
    second.location = first.location.model_copy()
    seen = []

    def similarity(a: str, b: str) -> float:
        seen.append((a, b))
        return 0.125

    result = build_clusters([first, second], similarity)[0]
    assert len(seen) == 1 and result.links[0].text_sim == 0.125


def test_naive_dates_rejected_consistently(rows: list[Report]) -> None:
    row = rows[0].model_copy(
        update={"created_at": rows[0].created_at.replace(tzinfo=None)}
    )
    with pytest.raises(ValueError, match="timezone"):
        build_clusters([row])
    with pytest.raises(ValueError, match="timezone"):
        build_clusters([row, rows[1]])


def test_port_constants() -> None:
    assert (
        clusters.DUP_SURE_RADIUS_M,
        clusters.DUP_RADIUS_M,
        clusters.DUP_TEXT_SIM,
        clusters.DUP_WINDOW_DAYS,
    ) == (50, 100, 0.5, 30)
