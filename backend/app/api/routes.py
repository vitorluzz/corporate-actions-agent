"""API routes for the review console."""

from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from app.agent.runner import process_document, run_batch, summarize
from app.api.deps import get_golden_base, get_session
from app.api.schemas import (
    AuditEventOut,
    CreateProjectRequest,
    DocumentListItem,
    ProjectOut,
    RenameProjectRequest,
    ReviewRequest,
)
from app.config import get_settings
from app.domain.golden import GoldenBase
from app.domain.schemas import DocumentResult
from app.extraction.pdf import render_page_png
from app.llm.factory import build_llm_client
from app.output.writer import _exceptions_json, _exceptions_markdown
from app.persistence import repository

router = APIRouter()


def _to_item(row) -> DocumentListItem:
    return DocumentListItem(
        id=row.id, source_file=row.source_file, doc_class=row.doc_class,
        event_type=row.event_type, decision=row.decision,
        human_status=row.human_status, dq_score=row.dq_score,
    )


def _doc_file_path(row) -> Path:
    settings = get_settings()
    if row.project_id:
        return settings.uploads_dir / row.project_id / row.source_file
    return settings.documents_dir / row.source_file


def _results(session: Session) -> list[DocumentResult]:
    return [DocumentResult.model_validate(r.result) for r in repository.list_documents(session)]


@router.post("/ingest")
def ingest(session: Session = Depends(get_session)) -> dict:
    results, summary = run_batch(get_settings())
    for r in results:
        repository.upsert_result(session, r)
    session.commit()
    return summary.model_dump(mode="json")


@router.get("/documents", response_model=list[DocumentListItem])
def list_documents(session: Session = Depends(get_session)) -> list[DocumentListItem]:
    return [_to_item(r) for r in repository.list_documents(session)]


@router.get("/review-queue", response_model=list[DocumentListItem])
def review_queue(session: Session = Depends(get_session)) -> list[DocumentListItem]:
    return [_to_item(r) for r in repository.review_queue(session)]


@router.get("/run-summary")
def run_summary(session: Session = Depends(get_session)) -> dict:
    rows = repository.list_documents(session)
    if not rows:
        return {"total": 0, "auto_approved": 0, "review": 0, "rejected": 0}
    results = [DocumentResult.model_validate(r.result) for r in rows]
    return summarize(rows[0].run_id, results).model_dump(mode="json")


@router.get("/exceptions-report")
def exceptions_report(session: Session = Depends(get_session)) -> dict:
    rows = repository.list_documents(session)
    results = [DocumentResult.model_validate(r.result) for r in rows]
    summary = summarize(rows[0].run_id if rows else "", results)
    return {"markdown": _exceptions_markdown(results, summary), "items": _exceptions_json(results)}


@router.get("/documents/{doc_id}")
def get_document(doc_id: str, session: Session = Depends(get_session)) -> dict:
    row = repository.get_document(session, doc_id)
    if row is None:
        raise HTTPException(status_code=404, detail="document not found")
    return {**row.result, "human_status": row.human_status}


@router.get("/documents/{doc_id}/pdf")
def get_pdf(doc_id: str, session: Session = Depends(get_session)) -> FileResponse:
    row = repository.get_document(session, doc_id)
    if row is None:
        raise HTTPException(status_code=404, detail="document not found")
    path = _doc_file_path(row)
    if not path.exists():
        raise HTTPException(status_code=404, detail="pdf file not found")
    # No `filename=` → served inline (Content-Disposition: inline).
    return FileResponse(path, media_type="application/pdf")


@router.get("/documents/{doc_id}/page.png")
def get_page_image(doc_id: str, session: Session = Depends(get_session)) -> Response:
    """Render page 1 of the document to PNG (robust display in any browser)."""
    row = repository.get_document(session, doc_id)
    if row is None:
        raise HTTPException(status_code=404, detail="document not found")
    path = _doc_file_path(row)
    if not path.exists():
        raise HTTPException(status_code=404, detail="pdf file not found")
    return Response(content=render_page_png(path, 1, dpi=150), media_type="image/png")


@router.get("/documents/{doc_id}/audit", response_model=list[AuditEventOut])
def get_audit(doc_id: str, session: Session = Depends(get_session)) -> list[AuditEventOut]:
    return [
        AuditEventOut(id=e.id, ts=e.ts.isoformat(), actor=e.actor, action=e.action, detail=e.detail or {})
        for e in repository.audit_trail(session, doc_id)
    ]


@router.post("/documents/{doc_id}/review")
def review(
    doc_id: str,
    body: ReviewRequest,
    session: Session = Depends(get_session),
    golden: GoldenBase = Depends(get_golden_base),
) -> dict:
    try:
        result = repository.apply_review(
            session, doc_id, actor=body.actor, decision=body.decision,
            field_corrections=body.field_corrections, note=body.note, golden=golden,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="document not found") from exc
    session.commit()
    row = repository.get_document(session, doc_id)
    return {**result.model_dump(mode="json"), "human_status": row.human_status}


# --------------------------------------------------------------------------- #
# Projects (CAA — Corporate Actions Agent)
# --------------------------------------------------------------------------- #
def _project_out(session: Session, proj) -> ProjectOut:
    prog = repository.project_progress(session, proj.id)
    return ProjectOut(
        id=proj.id, name=proj.name, status=proj.status, operator=proj.operator,
        created_at=proj.created_at.isoformat() if proj.created_at else "",
        total=prog["total"], decided=prog["decided"], pending=prog["pending"],
    )


def _list_uploaded(pid: str) -> list[dict]:
    updir = get_settings().uploads_dir / pid
    if not updir.exists():
        return []
    return [{"name": p.name, "size": p.stat().st_size} for p in sorted(updir.glob("*.pdf"))]


@router.post("/projects", response_model=ProjectOut)
def create_project(body: CreateProjectRequest, session: Session = Depends(get_session)) -> ProjectOut:
    proj = repository.create_project(session, body.name, operator=body.operator)
    session.commit()
    return _project_out(session, proj)


@router.get("/projects", response_model=list[ProjectOut])
def list_projects(session: Session = Depends(get_session)) -> list[ProjectOut]:
    return [_project_out(session, p) for p in repository.list_projects(session)]


@router.get("/projects/{pid}", response_model=ProjectOut)
def get_project(pid: str, session: Session = Depends(get_session)) -> ProjectOut:
    proj = repository.get_project(session, pid)
    if proj is None:
        raise HTTPException(status_code=404, detail="project not found")
    return _project_out(session, proj)


@router.patch("/projects/{pid}", response_model=ProjectOut)
def rename_project(
    pid: str, body: RenameProjectRequest, session: Session = Depends(get_session)
) -> ProjectOut:
    proj = repository.rename_project(session, pid, body.name)
    if proj is None:
        raise HTTPException(status_code=404, detail="project not found")
    session.commit()
    return _project_out(session, proj)


@router.delete("/projects/{pid}")
def delete_project(pid: str, session: Session = Depends(get_session)) -> dict:
    if not repository.delete_project(session, pid):
        raise HTTPException(status_code=404, detail="project not found")
    session.commit()
    updir = get_settings().uploads_dir / pid
    if updir.exists():
        shutil.rmtree(updir, ignore_errors=True)
    return {"deleted": pid}


@router.post("/projects/{pid}/files")
async def upload_files(
    pid: str,
    files: list[UploadFile] = File(...),
    session: Session = Depends(get_session),
) -> dict:
    if repository.get_project(session, pid) is None:
        raise HTTPException(status_code=404, detail="project not found")
    updir = get_settings().uploads_dir / pid
    updir.mkdir(parents=True, exist_ok=True)
    uploaded: list[str] = []
    for f in files:
        name = Path(f.filename or "arquivo.pdf").name
        if not name.lower().endswith(".pdf"):
            continue
        (updir / name).write_bytes(await f.read())
        uploaded.append(name)
    return {"uploaded": uploaded, "files": _list_uploaded(pid)}


@router.get("/projects/{pid}/files")
def list_uploaded_files(pid: str, session: Session = Depends(get_session)) -> dict:
    if repository.get_project(session, pid) is None:
        raise HTTPException(status_code=404, detail="project not found")
    return {"files": _list_uploaded(pid)}


@router.delete("/projects/{pid}/files/{filename}")
def delete_uploaded_file(pid: str, filename: str, session: Session = Depends(get_session)) -> dict:
    path = get_settings().uploads_dir / pid / Path(filename).name
    if path.exists():
        path.unlink()
    return {"files": _list_uploaded(pid)}


@router.post("/projects/{pid}/files/samples")
def load_sample_files(pid: str, session: Session = Depends(get_session)) -> dict:
    """Convenience: copy the bundled sample notices into the project (for demos)."""
    if repository.get_project(session, pid) is None:
        raise HTTPException(status_code=404, detail="project not found")
    settings = get_settings()
    updir = settings.uploads_dir / pid
    updir.mkdir(parents=True, exist_ok=True)
    for p in sorted(settings.documents_dir.glob("*.pdf")):
        shutil.copy(p, updir / p.name)
    return {"files": _list_uploaded(pid)}


@router.post("/projects/{pid}/analyze")
def analyze_project(
    pid: str,
    session: Session = Depends(get_session),
    golden: GoldenBase = Depends(get_golden_base),
) -> dict:
    proj = repository.get_project(session, pid)
    if proj is None:
        raise HTTPException(status_code=404, detail="project not found")
    settings = get_settings()
    pdfs = sorted((settings.uploads_dir / pid).glob("*.pdf"))
    if not pdfs:
        raise HTTPException(status_code=400, detail="nenhum arquivo para analisar")

    repository.set_project_status(session, pid, "ANALYZING")
    session.commit()

    llm = build_llm_client(settings)
    results = []
    for p in pdfs:
        try:
            res = process_document(p, llm=llm, golden=golden, settings=settings, run_id=pid)
            res.document.id = f"{pid}_{res.document.id}"
            repository.upsert_result(session, res, project_id=pid)
            results.append(res)
        except Exception as exc:  # resilient: one bad doc doesn't sink the analysis
            print(f"  ! falha ao processar {p.name}: {str(exc).splitlines()[0][:140]}")
    repository.set_project_status(session, pid, "REVIEW")
    session.commit()
    return summarize(pid, results).model_dump(mode="json")


@router.get("/projects/{pid}/documents", response_model=list[DocumentListItem])
def project_documents(pid: str, session: Session = Depends(get_session)) -> list[DocumentListItem]:
    return [_to_item(r) for r in repository.list_documents(session, pid)]


@router.get("/projects/{pid}/summary")
def project_summary(pid: str, session: Session = Depends(get_session)) -> dict:
    rows = repository.list_documents(session, pid)
    results = [DocumentResult.model_validate(r.result) for r in rows]
    payload = summarize(pid, results).model_dump(mode="json")
    payload["progress"] = repository.project_progress(session, pid)
    return payload


@router.post("/projects/{pid}/complete")
def complete_project(pid: str, session: Session = Depends(get_session)) -> dict:
    if repository.get_project(session, pid) is None:
        raise HTTPException(status_code=404, detail="project not found")
    prog = repository.project_progress(session, pid)
    if prog["pending"] > 0:
        raise HTTPException(
            status_code=400,
            detail=f"{prog['pending']} documento(s) ainda pendente(s) de decisão",
        )
    repository.set_project_status(session, pid, "COMPLETED")
    session.commit()
    return repository.project_report(session, pid)


@router.get("/projects/{pid}/report")
def get_project_report(pid: str, session: Session = Depends(get_session)) -> dict:
    try:
        return repository.project_report(session, pid)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="project not found") from exc


@router.get("/projects/{pid}/graph")
def get_project_graph(
    pid: str,
    session: Session = Depends(get_session),
    golden: GoldenBase = Depends(get_golden_base),
) -> dict:
    if repository.get_project(session, pid) is None:
        raise HTTPException(status_code=404, detail="project not found")
    return repository.build_project_graph(session, pid, golden)
