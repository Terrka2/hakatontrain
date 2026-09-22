"""Explicit C0 mutation audit; patches are restored after each pytest run."""

import logging
from pathlib import Path
from unittest.mock import patch

import pytest

logger = logging.getLogger(__name__)
AUTH_TEST = (
    "tests/blocks/test_skeleton_auth.py::test_signup_login_and_password_recovery"
)
STARTUP_TEST = (
    "tests/blocks/test_skeleton.py::test_startup_initializes_database_before_backend"
)
original_read_text = Path.read_text


def reversed_startup(path: Path, *args: object, **kwargs: object) -> str:
    if path.name == "prestart.sh":
        return "python app/initial_data.py\nalembic upgrade head\n"
    return original_read_text(path, *args, **kwargs)


def main() -> int:
    mutations = [
        (
            "constant email",
            patch("app.utils.render_email_template", return_value=""),
            AUTH_TEST,
        ),
        (
            "reversed startup",
            patch.object(Path, "read_text", reversed_startup),
            STARTUP_TEST,
        ),
        (
            "email renderer exception",
            patch(
                "app.utils.render_email_template", side_effect=RuntimeError("C0 mutant")
            ),
            AUTH_TEST,
        ),
    ]
    for name, mutation, target in mutations:
        with mutation:
            result = pytest.main([target, "-q", "--tb=short", "-p", "no:cacheprovider"])
        if result != pytest.ExitCode.TESTS_FAILED:
            logger.error("Mutation %s was not caught: %s", name, result)
            return 1
        logger.warning("Mutation caught: %s", name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
