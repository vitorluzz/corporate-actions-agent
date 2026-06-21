"""P6 tests: project lifecycle (create → upload → analyze → review → complete → report)."""

from __future__ import annotations

from collections import Counter

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings

DOCS = get_settings().documents_dir


def _create(client: TestClient, name: str = "Projeto Teste") -> str:
    return client.post("/projects", json={"name": name, "operator": "tester"}).json()["id"]


def test_create_rename_delete(client: TestClient) -> None:
    pid = _create(client, "Nome Original")
    assert client.get(f"/projects/{pid}").json()["name"] == "Nome Original"

    renamed = client.patch(f"/projects/{pid}", json={"name": "Nome Novo"}).json()
    assert renamed["name"] == "Nome Novo"

    assert client.delete(f"/projects/{pid}").json()["deleted"] == pid
    assert client.get(f"/projects/{pid}").status_code == 404
    assert all(p["id"] != pid for p in client.get("/projects").json())


def test_upload_and_remove_pdf(client: TestClient) -> None:
    pid = _create(client)
    # a tiny but valid-enough byte payload; a non-pdf name is ignored
    data = b"%PDF-1.4 fake"
    resp = client.post(
        f"/projects/{pid}/files",
        files=[
            ("files", ("aviso.pdf", data, "application/pdf")),
            ("files", ("notes.txt", b"ignore me", "text/plain")),
        ],
    ).json()
    names = [f["name"] for f in resp["files"]]
    assert names == ["aviso.pdf"]  # the .txt is rejected

    after = client.delete(f"/projects/{pid}/files/aviso.pdf").json()
    assert after["files"] == []


@pytest.mark.skipif(not DOCS.exists(), reason="document batch not present")
def test_full_lifecycle_samples_to_report(client: TestClient) -> None:
    pid = _create(client, "Eventos B3")

    # load the 8 bundled samples + analyze
    assert len(client.post(f"/projects/{pid}/files/samples").json()["files"]) == 8
    summary = client.post(f"/projects/{pid}/analyze").json()
    assert summary["total"] == 8 and summary["auto_approved"] == 3

    # project is now in review with 5 pending
    prog = client.get(f"/projects/{pid}/summary").json()["progress"]
    assert prog == {"total": 8, "decided": 3, "pending": 5}
    assert client.get(f"/projects/{pid}").json()["status"] == "REVIEW"

    # cannot finalize while documents are pending
    assert client.post(f"/projects/{pid}/complete").status_code == 400

    # operator approves every pending document
    for d in client.get(f"/projects/{pid}/documents").json():
        if d["decision"] != "AUTO_APPROVE" and not d["human_status"]:
            client.post(
                f"/documents/{d['id']}/review",
                json={"actor": "ana", "decision": "approve", "field_corrections": {}, "note": ""},
            )

    report = client.post(f"/projects/{pid}/complete").json()
    assert report["project"]["status"] == "COMPLETED"
    assert report["summary"]["total"] == 8
    assert report["summary"]["approved"] == 8
    assert len(report["documents"]) == 8


@pytest.mark.skipif(not DOCS.exists(), reason="document batch not present")
def test_correction_is_recorded_in_report(client: TestClient) -> None:
    pid = _create(client)
    client.post(f"/projects/{pid}/files/samples")
    client.post(f"/projects/{pid}/analyze")

    doc_id = f"{pid}_05_aurora_saneamento_dividendo_datas"
    client.post(
        f"/documents/{doc_id}/review",
        json={
            "actor": "ana",
            "decision": "approve",
            "field_corrections": {"data_pagamento": "2026-08-10"},
            "note": "data corrigida",
        },
    )
    report = client.get(f"/projects/{pid}/report").json()
    doc = next(d for d in report["documents"] if d["id"] == doc_id)
    assert any(c["field"] == "data_pagamento" for c in doc["corrections"])
    assert report["summary"]["corrections"] >= 1


def test_graph_unknown_project_404(client: TestClient) -> None:
    assert client.get("/projects/does-not-exist/graph").status_code == 404


def test_graph_empty_project_has_no_nodes(client: TestClient) -> None:
    pid = _create(client)
    graph = client.get(f"/projects/{pid}/graph").json()
    assert graph == {"nodes": [], "edges": []}


@pytest.mark.skipif(not DOCS.exists(), reason="document batch not present")
def test_project_graph_relationships(client: TestClient) -> None:
    pid = _create(client, "Grafo B3")
    client.post(f"/projects/{pid}/files/samples")
    client.post(f"/projects/{pid}/analyze")

    graph = client.get(f"/projects/{pid}/graph").json()
    docs = [n for n in graph["nodes"] if n["kind"] == "document"]
    entities = [n for n in graph["nodes"] if n["kind"] == "entity"]
    assert len(docs) == 8
    assert len(entities) == 8  # the sample batch has 8 distinct issuers

    # every document belongs to exactly one entity, and that entity exists
    entity_ids = {e["id"] for e in entities}
    belongs = [e for e in graph["edges"] if e["type"] == "belongs_to"]
    assert len(belongs) == 8
    for e in belongs:
        assert e["target"] in entity_ids
    for d in docs:
        assert d["entity"] in entity_ids

    by_type = Counter(e["type"] for e in graph["edges"])
    # distinct issuers ⇒ no duplicates; same event types ⇒ type links exist
    assert by_type["possible_duplicate"] == 0
    assert by_type["same_event_type"] >= 1
