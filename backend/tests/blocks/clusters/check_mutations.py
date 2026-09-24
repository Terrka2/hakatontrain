"""Run three isolated implementation mutations; never change source files."""

import os
import subprocess
import sys
from pathlib import Path

MUTATIONS = [
    (
        "constant",
        "return sorted(result, key=lambda c: c.id)",
        "return []",
        "test_fixture_count",
    ),
    (
        "strict-radius",
        "distance <= DUP_SURE_RADIUS_M",
        "distance < DUP_SURE_RADIUS_M",
        "test_distance_thresholds",
    ),
    (
        "lost-explanation",
        "links.append(DupLink(a=a.id, b=b.id, distance_m=distance, text_sim=sim))",
        "pass",
        "test_trio_links",
    ),
]


def main() -> int:
    source = Path(__file__).resolve().parents[3] / "app/blocks/clusters/l0.py"
    original = source.read_text(encoding="utf-8")
    for name, before, after, test in MUTATIONS:
        if original.count(before) != 1:
            raise RuntimeError(f"Mutation target is ambiguous: {name}")
        mutated = original.replace(before, after)
        script = (
            "import pytest; from app.blocks.clusters import l0; "
            f"exec(compile({mutated!r}, l0.__file__, 'exec'), l0.__dict__); "
            "raise SystemExit(pytest.main(['-q', '-p', 'no:cacheprovider', "
            f"'tests/blocks/clusters/test_clusters.py::{test}']))"
        )
        result = subprocess.run(
            [sys.executable, "-X", "utf8", "-c", script],
            cwd=source.parents[3],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        if result.returncode != 1 or "FAILED" not in result.stdout:
            sys.stderr.write(result.stdout + result.stderr)
            raise RuntimeError(f"Mutation survived or infrastructure failed: {name}")
        sys.stdout.write(f"Detected: {name}\n")
    if source.read_text(encoding="utf-8") != original:
        raise RuntimeError("Source changed during mutation check")
    sys.stdout.write("B3: 3/3 mutations detected; source unchanged\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
