"""Каркас C0: у каждого блока есть гнездо с портом. Тест падает, если кто-то сломал импорт блока."""

import importlib

import pytest

BLOCKS = {
    "operator": ["run_pipeline", "operator_run"],
    "ingest": ["load_fixture", "parse_file", "normalize"],
    "geo": [
        "haversine_m",
        "centroid",
        "within",
        "distance_to_polyline_m",
        "geocode",
        "h3_cell",
    ],
    "clusters": ["build_clusters"],
    "priority": ["score"],
    "context": ["get_weather", "build_context", "apply_weather_rules"],
    "dispatch": ["make_jobs", "solve", "replan", "baseline_total_priority"],
    "fieldwork": ["get_crew_route", "apply_update", "progress"],
    "search": ["embed", "text_similarity", "search"],
    "extractor": ["extract", "verify"],
    "assistant": ["handle", "confirm", "narrate"],
    "tools": ["call", "execute_pending", "REGISTRY"],
    "navigator": ["plan_trip"],
    "events": ["get_events", "enrich_context", "apply_deadlines"],
}


@pytest.mark.parametrize("name", sorted(BLOCKS))
def test_block_exposes_its_port(name: str) -> None:
    module = importlib.import_module(f"app.blocks.{name}")
    for attr in BLOCKS[name]:
        assert hasattr(module, attr), f"app.blocks.{name} потерял {attr}"
