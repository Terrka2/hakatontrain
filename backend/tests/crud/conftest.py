import pytest
from sqlmodel import Session


@pytest.fixture(scope="session", autouse=True)
def _use_db(db: Session) -> None:
    """Тесты этой папки работают с настоящей БД. Тесты блоков (tests/blocks) — без неё."""
