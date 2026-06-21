"""P5 tests: API + persistence + human-in-the-loop revalidation (on SQLite)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings

DOCS = get_settings().documents_dir


@pytest.fixture
def client(tmp_path) -> Iterator[TestClient]:
    settings = get_settings()
    original = settings.database_url
    settings.database_url = f"sqlite:///{tmp_path / 'api.db'}"
    from app.persistence import db

    db.reset_engine()
    from app.api.main import create_app

    with TestClient(create_app()) as c:
        yield c
    db.reset_engine()
    settings.database_url = original


@pytest.mark.skipif(not DOCS.exists(), reason="document batch not present")
def test_ingest_list_and_queue(client: TestClient) -> None:
    summary = client.post("/ingest").json()
    assert summary["total"] == 8
    assert summary["auto_approved"] == 3
    assert len(client.get("/documents").json()) == 8
    queue_ids = {d["id"] for d in client.get("/review-queue").json()}
    assert "05_aurora_saneamento_dividendo_datas" in queue_ids
    assert "08_construtora_horizonte_bonificacao" in queue_ids


@pytest.mark.skipif(not DOCS.exists(), reason="document batch not present")
def test_human_correction_revalidates_and_audits(client: TestClient) -> None:
    client.post("/ingest")
    doc_id = "05_aurora_saneamento_dividendo_datas"
    assert client.get(f"/documents/{doc_id}").json()["routing"]["decision"] == "HUMAN_REVIEW"

    # fix the payment date so it falls after the ex date -> date_order passes
    resp = client.post(
        f"/documents/{doc_id}/review",
        json={
            "actor": "ana",
            "decision": "approve",
            "field_corrections": {"data_pagamento": "2026-08-10"},
            "note": "data corrigida conforme aviso",
        },
    ).json()
    assert resp["routing"]["decision"] == "AUTO_APPROVE"
    assert resp["human_status"] == "APPROVED"

    actions = [e["action"] for e in client.get(f"/documents/{doc_id}/audit").json()]
    assert actions == ["ingested", "field_correction", "decision:approve"]

    # corrected doc leaves the review queue
    assert doc_id not in {d["id"] for d in client.get("/review-queue").json()}


@pytest.mark.skipif(not DOCS.exists(), reason="document batch not present")
def test_pdf_and_exceptions_report(client: TestClient) -> None:
    client.post("/ingest")
    pdf = client.get("/documents/02_banco_meridional_jcp/pdf")
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"

    report = client.get("/exceptions-report").json()
    assert "Relatório de Exceções" in report["markdown"]
    assert len(report["items"]) == 5
