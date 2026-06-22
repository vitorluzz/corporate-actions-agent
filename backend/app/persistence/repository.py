"""Repository: persistence + the human-in-the-loop review (revalidation) logic.

Review corrections are applied to the record, the deterministic guardrails /
golden match / DQ / routing are **re-run** (revalidation), the document's current
state is updated, and every action is appended to the immutable audit log. This
is the persist-and-revalidate HITL: simpler and more debuggable than resuming a
paused graph, while preserving full auditability (see README trade-offs).
"""

from __future__ import annotations

import uuid
from collections import Counter
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.routing import decide_routing
from app.config.settings import Settings, get_settings
from app.domain.enums import DocumentClass, RoutingDecision
from app.domain.golden import GoldenBase, normalize_issuer
from app.domain.parsing import parse_br_date, parse_br_decimal, parse_percent
from app.domain.schemas import Confidence, DocumentResult, ExtractedField, Validation
from app.guardrails.runner import run_guardrails
from app.persistence.models import AuditEvent, DocumentRow, Project
from app.validation.dq import compute_dq_score
from app.validation.golden_match import resolve_identity

_HUMAN_CONF = Confidence(p_correct=0.99, p_uncertain=0.01, p_error=0.0)
_DATE_ATTRS = {"data_aprovacao", "data_com", "data_ex", "data_pagamento"}
_DECIMAL_ATTRS = {"valor", "valor_bruto", "valor_liquido"}


def _coerce(attr: str, value: str | None):
    if value in (None, ""):
        return None
    if attr in _DATE_ATTRS:
        return parse_br_date(value)
    if attr in _DECIMAL_ATTRS:
        return parse_br_decimal(value)
    if attr == "irrf_rate":
        return parse_percent(value)
    return value.strip()


def upsert_result(
    session: Session, result: DocumentResult, *, project_id: str | None = None
) -> DocumentRow:
    row = session.get(DocumentRow, result.document.id)
    payload = result.model_dump(mode="json")
    is_new = row is None
    if row is None:
        row = DocumentRow(id=result.document.id)
        session.add(row)
    if project_id is not None:
        row.project_id = project_id
    row.source_file = result.document.source_file
    row.run_id = result.document.run_id
    row.doc_class = result.document.doc_class.value
    row.event_type = result.event_type.argmax.value
    row.decision = result.routing.decision.value
    row.dq_score = result.validation.dq_score.score
    row.result = payload
    if is_new:
        session.add(
            AuditEvent(
                document_id=row.id, actor="system", action="ingested",
                detail={"decision": row.decision, "event_type": row.event_type},
            )
        )
    session.flush()
    return row


def list_documents(session: Session, project_id: str | None = None) -> list[DocumentRow]:
    stmt = select(DocumentRow).order_by(DocumentRow.id)
    if project_id is not None:
        stmt = stmt.where(DocumentRow.project_id == project_id)
    return list(session.scalars(stmt))


def get_document(session: Session, doc_id: str) -> DocumentRow | None:
    return session.get(DocumentRow, doc_id)


def review_queue(session: Session, project_id: str | None = None) -> list[DocumentRow]:
    stmt = (
        select(DocumentRow)
        .where(DocumentRow.decision != RoutingDecision.AUTO_APPROVE.value)
        .where(DocumentRow.human_status.is_(None))
        .order_by(DocumentRow.id)
    )
    if project_id is not None:
        stmt = stmt.where(DocumentRow.project_id == project_id)
    return list(session.scalars(stmt))


def audit_trail(session: Session, doc_id: str) -> list[AuditEvent]:
    stmt = select(AuditEvent).where(AuditEvent.document_id == doc_id).order_by(AuditEvent.id)
    return list(session.scalars(stmt))


def _revalidate(
    result: DocumentResult, golden: GoldenBase, settings: Settings
) -> DocumentResult:
    gm = resolve_identity(result.record, golden)
    guards = run_guardrails(result.record, result.fields, settings)
    dq = compute_dq_score(
        guardrails=guards, fields=result.fields,
        golden_status=gm.status, type_confidence=result.event_type.confidence,
    )
    result.routing = decide_routing(
        record=result.record, fields=result.fields, event_type=result.event_type,
        guardrails=guards, golden_match=gm, dq=dq, settings=settings,
        is_scanned=result.document.doc_class is DocumentClass.SCANNED,
    )
    result.validation = Validation(golden_match=gm, coherence_checks=guards, dq_score=dq)
    return result


def apply_review(
    session: Session,
    doc_id: str,
    *,
    actor: str,
    decision: str,
    field_corrections: dict[str, str] | None = None,
    note: str = "",
    golden: GoldenBase | None = None,
    settings: Settings | None = None,
) -> DocumentResult:
    settings = settings or get_settings()
    golden = golden or GoldenBase.from_csv(settings.golden_records_csv)
    row = session.get(DocumentRow, doc_id)
    if row is None:
        raise KeyError(doc_id)

    result = DocumentResult.model_validate(row.result)
    corrections = field_corrections or {}

    for name, new_value in corrections.items():
        old = getattr(result.record, name, None)
        if hasattr(result.record, name):
            setattr(result.record, name, _coerce(name, new_value))
        field = next((f for f in result.fields if f.name == name), None)
        if field is None:
            field = ExtractedField(name=name, value=new_value, confidence=_HUMAN_CONF)
            result.fields.append(field)
        field.value = new_value
        field.grounded = True
        field.confidence = _HUMAN_CONF
        field.rationale = f"corrigido por operador ({actor})"
        session.add(
            AuditEvent(
                document_id=doc_id, actor=actor, action="field_correction",
                detail={"field": name, "old": _json_safe(old), "new": new_value},
            )
        )

    if corrections:
        result = _revalidate(result, golden, settings)

    row.human_status = {"approve": "APPROVED", "reject": "REJECTED"}.get(decision, "REVIEWED")
    row.decision = result.routing.decision.value
    row.event_type = result.event_type.argmax.value
    row.dq_score = result.validation.dq_score.score
    row.result = result.model_dump(mode="json")
    session.add(
        AuditEvent(
            document_id=doc_id, actor=actor, action=f"decision:{decision}",
            detail={"note": note, "resulting_routing": row.decision, "human_status": row.human_status},
        )
    )
    session.flush()
    return result


def _json_safe(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, (date, Decimal)):
        return str(value)
    return str(value)


# --------------------------------------------------------------------------- #
# Projects (CAA — Corporate Actions Agent)
# --------------------------------------------------------------------------- #
def create_project(session: Session, name: str, *, operator: str | None = None) -> Project:
    proj = Project(
        id=uuid.uuid4().hex[:12],
        name=(name or "").strip() or "Projeto sem nome",
        operator=operator,
        status="DRAFT",
    )
    session.add(proj)
    session.flush()
    return proj


def get_project(session: Session, project_id: str) -> Project | None:
    return session.get(Project, project_id)


def list_projects(session: Session) -> list[Project]:
    return list(session.scalars(select(Project).order_by(Project.created_at.desc())))


def set_project_status(session: Session, project_id: str, status: str) -> None:
    proj = session.get(Project, project_id)
    if proj is None:
        return
    proj.status = status
    if status == "COMPLETED":
        proj.completed_at = datetime.now(UTC)
    session.flush()


def rename_project(session: Session, project_id: str, name: str) -> Project | None:
    proj = session.get(Project, project_id)
    if proj is None:
        return None
    if name and name.strip():
        proj.name = name.strip()
    session.flush()
    return proj


def delete_project(session: Session, project_id: str) -> bool:
    proj = session.get(Project, project_id)
    if proj is None:
        return False
    session.delete(proj)  # cascades to documents + audit events
    session.flush()
    return True


def project_progress(session: Session, project_id: str) -> dict:
    docs = list_documents(session, project_id)
    total = len(docs)
    pending = sum(
        1 for d in docs
        if d.decision != RoutingDecision.AUTO_APPROVE.value and d.human_status is None
    )
    return {"total": total, "decided": total - pending, "pending": pending}


def project_report(session: Session, project_id: str) -> dict:
    proj = get_project(session, project_id)
    if proj is None:
        raise KeyError(project_id)
    docs = list_documents(session, project_id)

    doc_reports: list[dict] = []
    total_corrections = 0
    for d in docs:
        res = DocumentResult.model_validate(d.result)
        events = audit_trail(session, d.id)
        corrections = [e.detail for e in events if e.action == "field_correction"]
        decisions = [
            {"actor": e.actor, "action": e.action, "ts": e.ts.isoformat()}
            for e in events
            if e.action.startswith("decision:")
        ]
        total_corrections += len(corrections)
        doc_reports.append({
            "id": d.id,
            "source_file": d.source_file,
            "decision": d.decision,
            "human_status": d.human_status,
            "event_type": res.event_type.argmax.value,
            "dq_score": res.validation.dq_score.score,
            "record": res.record.model_dump(mode="json"),
            "golden_match": res.validation.golden_match.status.value,
            "reasons": res.routing.reasons,
            "corrections": corrections,
            "decisions": decisions,
        })

    decisions_count = Counter(d.decision for d in docs)
    approved = sum(
        1 for d in docs
        if d.human_status == "APPROVED"
        or (d.decision == RoutingDecision.AUTO_APPROVE.value and d.human_status is None)
    )
    rejected = sum(1 for d in docs if d.human_status == "REJECTED")
    return {
        "project": {
            "id": proj.id,
            "name": proj.name,
            "status": proj.status,
            "operator": proj.operator,
            "created_at": proj.created_at.isoformat() if proj.created_at else None,
            "completed_at": proj.completed_at.isoformat() if proj.completed_at else None,
        },
        "summary": {
            "total": len(docs),
            "auto_approved": decisions_count.get(RoutingDecision.AUTO_APPROVE.value, 0),
            "approved": approved,
            "rejected": rejected,
            "corrections": total_corrections,
        },
        "documents": doc_reports,
        "generated_at": datetime.now(UTC).isoformat(),
    }


# Fields compared across documents to *prove* a relationship (which field links two files).
GRAPH_COMPARE_FIELDS: list[tuple[str, str]] = [
    ("emissor", "Emissor"),
    ("cnpj", "CNPJ"),
    ("isin", "ISIN"),
    ("ticker", "Ticker"),
    ("evento", "Tipo de evento"),
    ("data_aprovacao", "Data aprovação"),
    ("data_com", "Data com"),
    ("data_ex", "Data ex"),
    ("data_pagamento", "Data pagamento"),
    ("valor", "Valor / provento"),
]

# A real duplicate needs more than the same event type — at least one of these must also match.
GRAPH_DUP_KEYS = ("data_aprovacao", "data_com", "data_ex", "data_pagamento", "valor")


def _graph_fmt(value: object) -> str | None:
    """Render a record value as a stable display string (or None when empty)."""
    if value is None:
        return None
    if isinstance(value, date):  # date and datetime
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value.normalize(), "f")  # drop trailing zeros, no sci-notation
    text = str(value).strip()
    return text or None


def _graph_norm(key: str, value: str | None) -> str | None:
    """Normalised form used to decide whether two values are *the same*."""
    if not value:
        return None
    if key == "emissor":
        return normalize_issuer(value) or None
    return value.strip().lower()


def build_project_graph(session: Session, project_id: str, golden: GoldenBase) -> dict:
    """Traceability graph: emissor hubs + documents, with typed relationships.

    Derived purely from the persisted records — no extra LLM work. Each node carries
    the key record fields, and every edge carries ``shared``: the list of fields whose
    values are identical on both ends. That is the *evidence* that proves why two files
    are related (e.g. "mesmo ISIN" / "mesmo emissor + mesma data de pagamento").
    """
    parsed = [(d, DocumentResult.model_validate(d.result)) for d in list_documents(session, project_id)]

    def entity_key(d, res: DocumentResult) -> tuple[str, str]:
        gm = res.validation.golden_match
        name = gm.golden_emissor or res.record.emissor
        norm = normalize_issuer(name) if name else None
        if norm:
            return norm, name
        # Unresolved issuer (e.g. an unreadable scan) → a *private* hub per document.
        # Never merge distinct unknowns into one bogus "desconhecido" issuer.
        return f"unknown:{d.id}", name or "Emissor não identificado"

    def type_provisional(res: DocumentResult) -> bool:
        # The event-type classification is contested (substance conflict, e.g. dividendo↔JCP),
        # so any link drawn *from the type* is provisional until a human confirms it.
        return any(
            c.name == "event_type_substance" and c.status.value in ("FAIL", "WARN")
            for c in res.validation.coherence_checks
        )

    def doc_fields(res: DocumentResult) -> dict[str, str | None]:
        r = res.record
        return {
            "emissor": _graph_fmt(r.emissor),
            "cnpj": _graph_fmt(r.cnpj),
            "isin": _graph_fmt(r.isin),
            "ticker": _graph_fmt(r.ticker),
            "evento": res.event_type.argmax.value,
            "data_aprovacao": _graph_fmt(r.data_aprovacao),
            "data_com": _graph_fmt(r.data_com),
            "data_ex": _graph_fmt(r.data_ex),
            "data_pagamento": _graph_fmt(r.data_pagamento),
            "valor": _graph_fmt(r.valor if r.valor is not None else r.valor_bruto),
        }

    def shared(fa: dict[str, str | None], fb: dict[str, str | None]) -> list[str]:
        out = []
        for key, _ in GRAPH_COMPARE_FIELDS:
            a, b = _graph_norm(key, fa.get(key)), _graph_norm(key, fb.get(key))
            if a is not None and a == b:
                out.append(key)
        return out

    fields_by_id: dict[str, dict[str, str | None]] = {}
    entities: dict[str, dict] = {}
    nodes: list[dict] = []
    for d, res in parsed:
        key, name = entity_key(d, res)
        if key not in entities:
            rec = golden.by_ticker(res.record.ticker) or golden.by_isin(res.record.isin)
            ent_fields = {"emissor": _graph_fmt(name), "ticker": _graph_fmt(rec.ticker if rec else res.record.ticker)}
            entities[key] = {
                "id": f"entity:{key}",
                "kind": "entity",
                "label": name,
                "ticker": rec.ticker if rec else res.record.ticker,
                "segment": rec.segmento_listagem if rec else None,
                "known": rec is not None,
                "fields": ent_fields,
            }
            fields_by_id[entities[key]["id"]] = ent_fields
        df = doc_fields(res)
        fields_by_id[d.id] = df
        nodes.append({
            "id": d.id,
            "kind": "document",
            "label": d.source_file,
            "entity": entities[key]["id"],
            "issuer": name,
            "ticker": res.record.ticker,
            "isin": res.record.isin,
            "event_type": res.event_type.argmax.value,
            "decision": d.decision,
            "human_status": d.human_status,
            "dq_score": res.validation.dq_score.score,
            "golden_status": res.validation.golden_match.status.value,
            "fields": df,
        })
    nodes.extend(entities.values())

    edges: list[dict] = []
    for d, res in parsed:
        key, _ = entity_key(d, res)
        ent_id = entities[key]["id"]
        edges.append({
            "source": d.id, "target": ent_id, "type": "belongs_to", "label": "pertence ao emissor",
            "shared": shared(fields_by_id[d.id], fields_by_id[ent_id]),
        })

    for i in range(len(parsed)):
        di, ri = parsed[i]
        ki, _ = entity_key(di, ri)
        for j in range(i + 1, len(parsed)):
            dj, rj = parsed[j]
            kj, _ = entity_key(dj, rj)
            sf = shared(fields_by_id[di.id], fields_by_id[dj.id])
            ti, tj = ri.event_type.argmax, rj.event_type.argmax
            same_type = ti == tj and not ti.is_ambiguous
            same_issuer = ki == kj and not ki.startswith("unknown:")
            same_sec = bool(
                (ri.record.isin and ri.record.isin == rj.record.isin)
                or (ri.record.ticker and ri.record.ticker == rj.record.ticker)
            )
            # A duplicate needs more than the same type: an overlapping date or the same value.
            dup_signal = same_type and any(k in sf for k in GRAPH_DUP_KEYS)

            if same_issuer and dup_signal:
                edge = {"source": di.id, "target": dj.id, "type": "possible_duplicate",
                        "label": f"possível duplicidade ({ti.value})"}
            elif same_sec:
                edge = {"source": di.id, "target": dj.id, "type": "same_security",
                        "label": "mesmo ativo (ISIN/ticker)"}
            elif same_issuer and same_type:
                # Same issuer + same type, but not a duplicate (e.g. a recurring provento).
                edge = {"source": di.id, "target": dj.id, "type": "same_event_type",
                        "label": f"mesmo emissor · mesmo tipo ({ti.value})"}
            else:
                # Cross-issuer "same category" is noise, not traceability → draw nothing.
                continue

            if edge["type"] in ("same_event_type", "possible_duplicate") and (
                type_provisional(ri) or type_provisional(rj)
            ):
                edge["provisional"] = True
                edge["label"] += " · tipo em revisão"
            edge["shared"] = sf
            edges.append(edge)

    return {"nodes": nodes, "edges": edges, "field_meta": [{"key": k, "label": v} for k, v in GRAPH_COMPARE_FIELDS]}
