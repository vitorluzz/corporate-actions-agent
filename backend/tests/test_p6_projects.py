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
    assert graph["nodes"] == []
    assert graph["edges"] == []


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
    # 8 distinct issuers + 8 distinct securities ⇒ the only honest links are belongs_to.
    # Cross-issuer "same category" is intentionally NOT drawn (noise, not traceability).
    assert set(by_type) == {"belongs_to"}
    assert by_type["same_event_type"] == 0
    assert by_type["possible_duplicate"] == 0

    # the scanned doc: without OCR it has no resolvable issuer (1 private "unknown" hub);
    # with OCR (Tesseract) it now reads a named issuer (Telecom Norte) → 0 unknown hubs.
    # Either way, distinct unknowns are never merged into one bogus hub.
    from app.extraction.ocr import ocr_available

    expected_unknown = 0 if ocr_available() else 1
    assert len([e for e in entities if e["id"].startswith("entity:unknown:")]) == expected_unknown

    # field-level evidence stays attached to every edge
    assert [m["key"] for m in graph["field_meta"]][:1] == ["emissor"]
    assert all("shared" in e for e in graph["edges"])
    # the issuer link is field-proven (documents share the emissor with their hub)
    assert any("emissor" in e["shared"] for e in graph["edges"] if e["type"] == "belongs_to")
    # document nodes expose the comparable record fields
    assert all("fields" in n and "isin" in n["fields"] for n in docs)


@pytest.mark.skipif(not DOCS.exists(), reason="document batch not present")
def test_graph_duplicate_intraissuer_and_provisional(client: TestClient, full_golden) -> None:
    """Same issuer: identical notices = duplicate; recurring = same_event_type; a contested
    type (substance conflict) makes the link provisional. Built from a real stub result."""
    import copy

    from app.domain.schemas import DocumentResult
    from app.persistence import repository
    from app.persistence.db import get_sessionmaker

    seed = _create(client, "seed")
    client.post(f"/projects/{seed}/files/samples")
    client.post(f"/projects/{seed}/analyze")
    base = client.get(f"/documents/{seed}_01_energetica_vale_tiete_dividendo").json()
    base.pop("human_status", None)

    def make(doc_id: str, *, provisional: bool = False, **rec: str) -> DocumentResult:
        d = copy.deepcopy(base)
        d["document"]["id"] = doc_id
        d["document"]["source_file"] = f"{doc_id}.pdf"
        d["record"].update(rec)
        if provisional:
            d["validation"]["coherence_checks"].append(
                {"name": "event_type_substance", "status": "FAIL",
                 "message": "substância de JCP sob título de dividendo", "fields": ["tipo_evento"]}
            )
        return DocumentResult.model_validate(d)

    session_factory = get_sessionmaker()
    with session_factory() as s:
        pid = repository.create_project(s, "Dup/provisório").id
        repository.upsert_result(s, make("syn_A"), project_id=pid)
        repository.upsert_result(s, make("syn_B"), project_id=pid)  # identical to A → duplicate
        repository.upsert_result(  # same issuer, other security, other dates → same_event_type
            s, make("syn_C", isin="BRTIETACNPR1", ticker="TIET4", data_aprovacao="2025-01-02",
                    data_com="2025-01-09", data_ex="2025-01-10", data_pagamento="2025-02-01", valor="9.99"),
            project_id=pid,
        )
        repository.upsert_result(  # contested type → provisional links
            s, make("syn_T", provisional=True, isin="BRTIETACNPR9", ticker="TIET5",
                    data_aprovacao="2024-03-02", data_com="2024-03-09", data_ex="2024-03-10",
                    data_pagamento="2024-04-01", valor="7.77"),
            project_id=pid,
        )
        s.commit()
        graph = repository.build_project_graph(s, pid, full_golden)

    edges = graph["edges"]
    dup = [e for e in edges if e["type"] == "possible_duplicate"]
    assert len(dup) == 1
    assert {dup[0]["source"], dup[0]["target"]} == {"syn_A", "syn_B"}
    # the duplicate is justified by more than the type: a shared date or value
    assert any(k in dup[0]["shared"] for k in
               ("data_aprovacao", "data_com", "data_ex", "data_pagamento", "valor"))

    # same issuer + same type but NOT a duplicate ⇒ same_event_type (recurring provento)
    assert [e for e in edges if e["type"] == "same_event_type"]

    # a contested-type document only yields *provisional* type links
    prov = [e for e in edges if e.get("provisional")]
    assert prov
    assert all("syn_T" in (e["source"], e["target"]) for e in prov)
    assert all(e["type"] == "same_event_type" for e in prov)


@pytest.mark.skipif(not DOCS.exists(), reason="document batch not present")
def test_certificate_pdf_gated_by_approval(client: TestClient) -> None:
    pid = _create(client, "Certificados")
    client.post(f"/projects/{pid}/files/samples")
    client.post(f"/projects/{pid}/analyze")
    docs = client.get(f"/projects/{pid}/documents").json()
    approved = next(d for d in docs if d["decision"] == "AUTO_APPROVE")
    pending = next(d for d in docs if d["decision"] != "AUTO_APPROVE" and not d["human_status"])

    # not approved yet → 409 (and the UI hides the button)
    assert client.get(f"/documents/{pending['id']}/certificate.pdf").status_code == 409

    # auto-approved → a real, branded PDF
    r = client.get(f"/documents/{approved['id']}/certificate.pdf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:5] == b"%PDF-"
    assert "attachment" in r.headers["content-disposition"]

    # once the operator approves the pending one, its certificate unlocks
    client.post(
        f"/documents/{pending['id']}/review",
        json={"actor": "ana", "decision": "approve", "field_corrections": {}, "note": ""},
    )
    assert client.get(f"/documents/{pending['id']}/certificate.pdf").status_code == 200

    assert client.get("/documents/does-not-exist/certificate.pdf").status_code == 404


@pytest.mark.skipif(not DOCS.exists(), reason="document batch not present")
def test_project_report_pdf(client: TestClient) -> None:
    pid = _create(client, "Relatório PDF")
    client.post(f"/projects/{pid}/files/samples")
    client.post(f"/projects/{pid}/analyze")
    r = client.get(f"/projects/{pid}/report.pdf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:5] == b"%PDF-"
    assert "attachment" in r.headers["content-disposition"]
    assert client.get("/projects/does-not-exist/report.pdf").status_code == 404
