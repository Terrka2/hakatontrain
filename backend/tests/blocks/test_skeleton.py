"""C0: offline acceptance checks for startup wiring and shared fixture."""

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]


def test_startup_initializes_database_before_backend() -> None:
    services = yaml.safe_load((ROOT / "compose.yml").read_text())["services"]
    prestart = services["prestart"]
    assert prestart["command"] == ["bash", "scripts/prestart.sh"]
    assert prestart["depends_on"]["db"]["condition"] == "service_healthy"
    assert services["backend"]["depends_on"]["prestart"]["condition"] == (
        "service_completed_successfully"
    )
    assert prestart["environment"] == services["backend"]["environment"]
    script = (ROOT / "backend/scripts/prestart.sh").read_text()
    assert script.index("alembic upgrade head") < script.index(
        "python app/initial_data.py"
    )


def test_frontend_uses_the_canonical_fixture() -> None:
    backend = json.loads(
        (ROOT / "backend/app/fixtures/demo_city.json").read_text(encoding="utf-8")
    )
    frontend = json.loads(
        (ROOT / "frontend/src/mocks/demo_city.json").read_text(encoding="utf-8")
    )
    assert frontend == backend


def test_core_frontend_nests_exist() -> None:
    for name in ("map", "queue", "dispatch", "assistant", "crew"):
        assert (ROOT / f"frontend/src/features/{name}/index.ts").is_file()
