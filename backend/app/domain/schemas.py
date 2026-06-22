"""Output schema — the auditable **data contract** per document.

Design goal (from the case): an Asset Servicing operator must *trust the record
and audit every value without reopening the document*. Therefore every value
carries: (a) what was extracted, (b) where from (provenance/lineage),
(c) how reliable it is (ternary confidence), (d) validation vs. the golden base,
and (e) what needs human review and why.

The ternary confidence ``{p_correct, p_uncertain, p_error}`` mirrors the
``P(Chave)/P(Valor)/P(Incerto)`` distribution from the COBOL PoC, re-applied to
financial fields.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.enums import (
    ConfidenceLabel,
    DocumentClass,
    EventType,
    EvidenceSource,
    GoldenMatchStatus,
    GuardrailStatus,
    RoutingDecision,
    Severity,
)


# --------------------------------------------------------------------------- #
# Provenance / lineage
# --------------------------------------------------------------------------- #
class BBox(BaseModel):
    """Bounding box. ``coord_system`` distinguishes native PDF points from the
    normalized 0–1000 space returned by Gemini spatial grounding on scans."""

    model_config = ConfigDict(frozen=True)

    x0: float
    y0: float
    x1: float
    y1: float
    coord_system: str = "pdf_points"  # or "normalized_0_1000"


class Evidence(BaseModel):
    """Where a value came from — the lineage anchor for auditability."""

    source: EvidenceSource
    quote: str | None = None
    page: int | None = None
    bbox: BBox | None = None
    char_span: tuple[int, int] | None = None
    match_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Fuzzy score of value↔source anchoring (groundedness signal).",
    )


# --------------------------------------------------------------------------- #
# Confidence (ternary distribution)
# --------------------------------------------------------------------------- #
class Confidence(BaseModel):
    """Ternary confidence ~ P(Chave)/P(Valor)/P(Incerto).

    ``p_correct`` ~ value is right; ``p_uncertain`` ~ ambiguous/low-signal;
    ``p_error`` ~ value likely wrong/missing. Components are normalized to sum 1.
    """

    p_correct: float = Field(ge=0.0, le=1.0)
    p_uncertain: float = Field(ge=0.0, le=1.0)
    p_error: float = Field(ge=0.0, le=1.0)

    @classmethod
    def from_raw(cls, p_correct: float, p_uncertain: float, p_error: float) -> Confidence:
        """Build from arbitrary non-negative raw scores (clamped, then normalized)."""
        pc, pu, pe = max(0.0, p_correct), max(0.0, p_uncertain), max(0.0, p_error)
        total = pc + pu + pe
        if total <= 0:
            return cls(p_correct=0.0, p_uncertain=1.0, p_error=0.0)
        return cls(p_correct=pc / total, p_uncertain=pu / total, p_error=pe / total)

    @model_validator(mode="after")
    def _normalize(self) -> Confidence:
        total = self.p_correct + self.p_uncertain + self.p_error
        if total <= 0:
            object.__setattr__(self, "p_correct", 0.0)
            object.__setattr__(self, "p_uncertain", 1.0)
            object.__setattr__(self, "p_error", 0.0)
        elif abs(total - 1.0) > 1e-6:
            object.__setattr__(self, "p_correct", self.p_correct / total)
            object.__setattr__(self, "p_uncertain", self.p_uncertain / total)
            object.__setattr__(self, "p_error", self.p_error / total)
        return self

    @property
    def label(self) -> ConfidenceLabel:
        if self.p_correct >= 0.80:
            return ConfidenceLabel.HIGH
        if self.p_correct >= 0.55:
            return ConfidenceLabel.MEDIUM
        return ConfidenceLabel.LOW


# --------------------------------------------------------------------------- #
# Guardrails / validation
# --------------------------------------------------------------------------- #
class GuardrailResult(BaseModel):
    """Outcome of one deterministic check (also a Data Quality test result)."""

    name: str
    status: GuardrailStatus
    severity: Severity = Severity.WARNING
    message: str = ""
    fields: list[str] = Field(default_factory=list)


class Discrepancy(BaseModel):
    field: str
    extracted: str | None = None
    reference: str | None = None
    note: str = ""


class GoldenMatch(BaseModel):
    """Result of cross-referencing identity against ``golden_records.csv``.

    ``explanation`` makes the entity-resolution decision human-readable
    (why it matched / why it diverged)."""

    status: GoldenMatchStatus
    matched_on: list[str] = Field(default_factory=list)
    discrepancies: list[Discrepancy] = Field(default_factory=list)
    explanation: str = ""
    golden_emissor: str | None = None
    golden_isin: str | None = None
    golden_ticker: str | None = None


class DataQualityScore(BaseModel):
    """Composite Data Quality scorecard for the record (0–1)."""

    score: float = Field(ge=0.0, le=1.0)
    components: dict[str, float] = Field(default_factory=dict)

    @property
    def label(self) -> ConfidenceLabel:
        if self.score >= 0.80:
            return ConfidenceLabel.HIGH
        if self.score >= 0.55:
            return ConfidenceLabel.MEDIUM
        return ConfidenceLabel.LOW


class Validation(BaseModel):
    golden_match: GoldenMatch
    coherence_checks: list[GuardrailResult] = Field(default_factory=list)
    dq_score: DataQualityScore


# --------------------------------------------------------------------------- #
# Extracted fields & record
# --------------------------------------------------------------------------- #
class ExtractedField(BaseModel):
    """A single extracted field with full audit metadata."""

    name: str
    value: str | None = None
    confidence: Confidence
    evidence: Evidence | None = None
    grounded: bool = False
    rationale: str = ""


class EventTypeDistribution(BaseModel):
    """Probabilistic event-type classification (self-consistency)."""

    distribution: dict[EventType, float] = Field(default_factory=dict)
    argmax: EventType = EventType.INCERTO
    entropy: float = 1.0          # normalized [0,1]
    confidence: float = 0.0       # 1 - entropy
    samples: int = 0

    @field_validator("distribution")
    @classmethod
    def _check_distribution(cls, v: dict[EventType, float]) -> dict[EventType, float]:
        total = sum(v.values())
        if total > 0 and abs(total - 1.0) > 1e-3:
            return {k: val / total for k, val in v.items()}
        return v


class Record(BaseModel):
    """The clean structured record (typed values) consumed downstream."""

    emissor: str | None = None
    cnpj: str | None = None
    isin: str | None = None
    ticker: str | None = None
    tipo_evento: EventType | None = None
    data_aprovacao: date | None = None
    data_com: date | None = None
    data_ex: date | None = None
    data_pagamento: date | None = None
    valor: Decimal | None = None
    valor_bruto: Decimal | None = None
    valor_liquido: Decimal | None = None
    irrf_rate: Decimal | None = None
    proporcao: str | None = None
    moeda: str | None = "BRL"


# --------------------------------------------------------------------------- #
# Routing / audit / document
# --------------------------------------------------------------------------- #
class Routing(BaseModel):
    decision: RoutingDecision
    reasons: list[str] = Field(default_factory=list)
    required_human_actions: list[str] = Field(default_factory=list)


class SamplingParams(BaseModel):
    n: int
    temperature: float


class ToolCall(BaseModel):
    tool: str
    arguments: dict = Field(default_factory=dict)
    result_summary: str = ""


class Audit(BaseModel):
    created_at: datetime
    sampling: SamplingParams
    tool_calls: list[ToolCall] = Field(default_factory=list)
    versions: dict[str, str] = Field(default_factory=dict)


class DocumentMeta(BaseModel):
    id: str
    source_file: str
    pages: int = 0
    doc_class: DocumentClass = DocumentClass.NATIVE
    extraction_method: str = ""
    model: str = ""
    model_version: str | None = None
    prompt_hash: str | None = None
    run_id: str = ""
    doc_hash: str = ""


class DocumentResult(BaseModel):
    """The per-document JSON deliverable."""

    document: DocumentMeta
    record: Record
    event_type: EventTypeDistribution
    fields: list[ExtractedField] = Field(default_factory=list)
    validation: Validation
    routing: Routing
    audit: Audit


# --------------------------------------------------------------------------- #
# Batch-level observability
# --------------------------------------------------------------------------- #
class RunSummary(BaseModel):
    """Batch-level observability for the operator (the exceptions-report header)."""

    run_id: str
    created_at: datetime
    total: int = 0
    auto_approved: int = 0
    review: int = 0
    rejected: int = 0
    auto_rate: float = 0.0
    avg_confidence: float = 0.0
    type_mix: dict[str, int] = Field(default_factory=dict)
    flag_reasons_histogram: dict[str, int] = Field(default_factory=dict)
