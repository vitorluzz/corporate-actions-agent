"""FastAPI dependencies."""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy.orm import Session

from app.config import get_settings
from app.domain.golden import GoldenBase
from app.persistence import get_sessionmaker


def get_session() -> Iterator[Session]:
    session = get_sessionmaker()()
    try:
        yield session
    finally:
        session.close()


@lru_cache
def get_golden_base() -> GoldenBase:
    return GoldenBase.from_csv(get_settings().golden_records_csv)
