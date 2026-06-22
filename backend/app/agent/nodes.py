"""Pipeline nodes (the agent's reasoning steps) + result assembly.

Deps (LLM client, golden base, settings) are injected into an ``AgentNodes``
instance so the graph state stays pure data and checkpointable. Each node is a
small, testable transformation of ``PipelineState``.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app import __version__
from app.agent.assembly import apply_guardrail_signal, assemble
from app.agent.crossmodal import build_ocr_consensus, crosscheck_guardrail, crossmodal_map
from app.agent.routing import decide_routing
from app.agent.selfconsistency import aggregate
from app.agent.state import PipelineState
from app.config.settings import Settings
from app.domain.enums import DocumentClass, GuardrailStatus
from app.domain.golden import GoldenBase
from app.domain.schemas import (
    Audit,
    DocumentMeta,
    DocumentResult,
    SamplingParams,
    ToolCall,
    Validation,
)
from app.guardrails.runner import run_guardrails
from app.llm.base import ExtractionInput, LLMClient, prompt_hash
from app.llm.prompts import EXTRACTION_INSTRUCTION, SYSTEM_PROMPT
from app.validation.dq import compute_dq_score
from app.validation.golden_match import resolve_identity

_PROMPT_HASH = prompt_hash(SYSTEM_PROMPT, EXTRACTION_INSTRUCTION)


def _extraction_method(is_scan: bool, provider: str, full_text: str) -> str:
    if not is_scan:
        return "native_text+bbox"
    if "gemini" in provider:
        return "gemini_vision"
    if full_text.strip():
        return "tesseract_ocr"
    return "scanned_no_text"


class AgentNodes:
    def __init__(self, llm: LLMClient, golden: GoldenBase, settings: Settings) -> None:
        self.llm = llm
        self.golden = golden
        self.settings = settings

    # -- nodes --------------------------------------------------------------
    def extract(self, state: PipelineState) -> PipelineState:
        doc = state.doc
        is_scan = doc.doc_class is DocumentClass.SCANNED
        inp = ExtractionInput(
            doc_id=doc.doc_id,
            doc_hash=doc.doc_hash,
            # OCR (when available) gives a scanned doc a text layer the offline extractor can
            # parse; vision providers still receive the page image below.
            text=doc.full_text or None,
            image_b64=doc.images_b64 if is_scan else [],
            is_scan=is_scan,
        )
        state.samples = [
            self.llm.extract(
                inp,
                temperature=self.settings.self_consistency_temperature,
                sample_index=i,
            )
            for i in range(self.settings.self_consistency_n)
        ]
        # Cross-modal: when a scan was read by vision, also run the deterministic
        # OCR-text extractor as an *independent* second vote (anchor + verify).
        if is_scan and "gemini" in self.llm.name and doc.full_text.strip():
            state.ocr_consensus = build_ocr_consensus(doc, self.settings)
        return state

    def classify_and_assemble(self, state: PipelineState) -> PipelineState:
        state.consensus = aggregate(state.samples)
        state.crossmodal = crossmodal_map(
            state.consensus, state.ocr_consensus, state.doc.full_text
        )
        record, fields, signals = assemble(
            state.consensus, state.doc, self.settings, crossmodal=state.crossmodal
        )
        state.record, state.fields, state.signals = record, fields, signals
        return state

    def validate(self, state: PipelineState) -> PipelineState:
        assert state.record is not None
        gm = resolve_identity(state.record, self.golden)
        state.golden_match = gm
        state.tool_calls.append(
            ToolCall(
                tool="lookup_golden_record",
                arguments={"isin": state.record.isin, "ticker": state.record.ticker},
                result_summary=f"{gm.status.value}: {gm.explanation}",
            )
        )
        guards = run_guardrails(state.record, state.fields, self.settings)
        # Cross-modal coherence: vision↔OCR disagreements on a scan are auditable
        # signals that escalate the affected fields (and the document) for review.
        if state.crossmodal:
            guards.append(crosscheck_guardrail(state.crossmodal))
        state.guardrails = guards
        for g in guards:
            state.tool_calls.append(
                ToolCall(tool=g.name, result_summary=f"{g.status.value} — {g.message}")
            )
        failed_fields: set[str] = set()
        for g in guards:
            if g.status is GuardrailStatus.FAIL:
                failed_fields.update(g.fields)
        state.fields = apply_guardrail_signal(state.fields, state.signals, failed_fields)
        return state

    def score(self, state: PipelineState) -> PipelineState:
        assert state.consensus is not None and state.golden_match is not None
        state.dq = compute_dq_score(
            guardrails=state.guardrails,
            fields=state.fields,
            golden_status=state.golden_match.status,
            type_confidence=state.consensus.event_type.confidence,
        )
        return state

    def route(self, state: PipelineState) -> PipelineState:
        assert state.record and state.consensus and state.golden_match and state.dq
        state.routing = decide_routing(
            record=state.record,
            fields=state.fields,
            event_type=state.consensus.event_type,
            guardrails=state.guardrails,
            golden_match=state.golden_match,
            dq=state.dq,
            settings=self.settings,
            is_scanned=state.doc.doc_class is DocumentClass.SCANNED,
        )
        return state

    def finalize(self, state: PipelineState) -> PipelineState:
        state.result = self._build_result(state)
        return state

    # -- result assembly ----------------------------------------------------
    def _build_result(self, state: PipelineState) -> DocumentResult:
        doc = state.doc
        is_scan = doc.doc_class is DocumentClass.SCANNED
        assert state.record and state.consensus and state.golden_match and state.dq and state.routing

        meta = DocumentMeta(
            id=doc.doc_id,
            source_file=doc.source_file,
            pages=doc.page_count,
            doc_class=doc.doc_class,
            extraction_method=_extraction_method(is_scan, self.llm.name, doc.full_text),
            model=self.llm.model,
            prompt_hash=_PROMPT_HASH,
            run_id=state.run_id,
            doc_hash=doc.doc_hash,
        )
        audit = Audit(
            created_at=datetime.now(UTC),
            sampling=SamplingParams(
                n=self.settings.self_consistency_n,
                temperature=self.settings.self_consistency_temperature,
            ),
            tool_calls=state.tool_calls,
            versions={"app": __version__, "llm": f"{self.llm.name}:{self.llm.model}"},
        )
        validation = Validation(
            golden_match=state.golden_match,
            coherence_checks=state.guardrails,
            dq_score=state.dq,
        )
        return DocumentResult(
            document=meta,
            record=state.record,
            event_type=state.consensus.event_type,
            fields=state.fields,
            validation=validation,
            routing=state.routing,
            audit=audit,
        )
