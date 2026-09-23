"""Explicit B0 mutation audit; all temporary implementation patches are restored."""

import logging
from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from app.blocks import operator
from app.blocks.operator import l0
from app.contracts.models import OperatorRun

log = logging.getLogger(__name__)


def main() -> int:
    constant = OperatorRun(
        id="mutant",
        trigger="manual",
        at=datetime(2026, 9, 26, tzinfo=UTC),
        reports_seen=0,
        clusters_total=0,
        clusters_new=0,
    )
    original = operator.get_clusters
    base = "tests/blocks/operator/"
    mutations = [
        (
            "constant run",
            patch.object(l0, "operator_run", return_value=constant),
            base + "test_operator.py::test_manual_run_links_plan_and_review",
        ),
        (
            "reversed priorities",
            patch.object(
                operator,
                "get_clusters",
                side_effect=lambda *a, **k: original(*a, **k)[::-1],
            ),
            base + "test_unit.py::test_api_filters_detail_review_and_runs",
        ),
        (
            "lost error containment",
            patch.object(l0, "_error", side_effect=RuntimeError("mutant")),
            base + "test_operator.py::test_real_dependency_failure[score]",
        ),
    ]
    for name, mutation, target in mutations:
        with mutation:
            result = pytest.main(
                [target, "-q", "-s", "--tb=no", "-p", "no:cacheprovider"]
            )
        if result != pytest.ExitCode.TESTS_FAILED:
            log.error("Mutation was not detected: %s (%s)", name, result)
            return 1
        log.warning("Mutation detected and restored: %s", name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
