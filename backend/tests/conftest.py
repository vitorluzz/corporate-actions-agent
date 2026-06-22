"""Shared pytest fixtures."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.domain.golden import GoldenBase, GoldenRecord


@pytest.fixture(autouse=True)
def _force_stub_provider() -> None:
    """Tests are hermetic: always use the offline stub, never the live LLM.

    Prevents a populated ``GOOGLE_API_KEY`` in ``.env`` from turning the
    integration tests into slow, non-deterministic, quota-spending Gemini calls.
    """
    settings = get_settings()
    original = settings.llm_provider
    settings.llm_provider = "stub"
    yield
    settings.llm_provider = original


@pytest.fixture
def client(tmp_path) -> Iterator[TestClient]:
    """API client backed by a throwaway SQLite DB + temp uploads dir."""
    settings = get_settings()
    original_db = settings.database_url
    original_uploads = settings.uploads_dir
    settings.database_url = f"sqlite:///{tmp_path / 'api.db'}"
    settings.uploads_dir = tmp_path / "uploads"

    from app.persistence import db

    db.reset_engine()
    from app.api.main import create_app

    with TestClient(create_app()) as c:
        yield c

    db.reset_engine()
    settings.database_url = original_db
    settings.uploads_dir = original_uploads


@pytest.fixture
def golden_base() -> GoldenBase:
    return GoldenBase.from_records(
        [
            GoldenRecord(
                emissor="Energética Vale do Tietê S.A.",
                cnpj="12.345.678/0001-90",
                isin="BRTIETACNOR3",
                ticker="TIET3",
                classe="ON",
                segmento_listagem="Novo Mercado",
                status="ativo",
            ),
            GoldenRecord(
                emissor="Banco Meridional do Brasil S.A.",
                cnpj="60.111.222/0001-55",
                isin="BRBMRDACNPR7",
                ticker="BMRD4",
                classe="PN",
                segmento_listagem="Nível 1",
                status="ativo",
            ),
        ]
    )


@pytest.fixture
def full_golden() -> GoldenBase:
    csv = get_settings().golden_records_csv
    if not csv.exists():
        pytest.skip("golden_records.csv not present")
    return GoldenBase.from_csv(csv)
