"""High-level runners: one document, or the whole batch + run summary."""

from __future__ import annotations

import sys
import uuid
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from statistics import fmean

from app.agent.nodes import AgentNodes
from app.agent.state import PipelineState
from app.config.settings import Settings, get_settings
from app.domain.golden import GoldenBase
from app.domain.schemas import DocumentResult, RunSummary
from app.extraction.pdf import load_document
from app.llm.base import LLMClient
from app.llm.factory import build_llm_client


def process_document(
    path: str | Path,
    *,
    llm: LLMClient,
    golden: GoldenBase,
    settings: Settings,
    run_id: str,
) -> DocumentResult:
    doc = load_document(path)
    nodes = AgentNodes(llm, golden, settings)
    state = PipelineState(doc=doc, run_id=run_id)
    for step in (
        nodes.extract,
        nodes.classify_and_assemble,
        nodes.validate,
        nodes.score,
        nodes.route,
        nodes.finalize,
    ):
        state = step(state)
    assert state.result is not None
    return state.result


def summarize(run_id: str, results: list[DocumentResult]) -> RunSummary:
    decisions = Counter(r.routing.decision.value for r in results)
    type_mix = Counter(r.event_type.argmax.value for r in results)
    flag_reasons: Counter[str] = Counter()
    confidences: list[float] = []
    for r in results:
        if r.routing.decision.value != "AUTO_APPROVE":
            for reason in r.routing.reasons:
                flag_reasons[reason.split(" (")[0].split(":")[0]] += 1
        confidences.extend(f.confidence.p_correct for f in r.fields if f.value)

    total = len(results)
    auto = decisions.get("AUTO_APPROVE", 0)
    return RunSummary(
        run_id=run_id,
        created_at=datetime.now(UTC),
        total=total,
        auto_approved=auto,
        review=decisions.get("HUMAN_REVIEW", 0),
        rejected=decisions.get("REJECT", 0),
        auto_rate=round(auto / total, 4) if total else 0.0,
        avg_confidence=round(fmean(confidences), 4) if confidences else 0.0,
        type_mix=dict(type_mix),
        flag_reasons_histogram=dict(flag_reasons),
    )


def run_batch(
    settings: Settings | None = None, *, run_id: str | None = None
) -> tuple[list[DocumentResult], RunSummary]:
    settings = settings or get_settings()
    run_id = run_id or uuid.uuid4().hex[:12]
    golden = GoldenBase.from_csv(settings.golden_records_csv)
    llm = build_llm_client(settings)

    pdfs = sorted(settings.documents_dir.glob("*.pdf"))
    results: list[DocumentResult] = []
    for p in pdfs:
        try:
            results.append(
                process_document(p, llm=llm, golden=golden, settings=settings, run_id=run_id)
            )
        except Exception as exc:  # resilient: a per-doc failure (e.g. quota) doesn't sink the batch
            print(f"  ! falha ao processar {p.name}: {str(exc).splitlines()[0][:140]}", file=sys.stderr)
    return results, summarize(run_id, results)
