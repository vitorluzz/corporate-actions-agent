"""Composite Data Quality scorecard for a record.

A transparent weighted blend of: guardrail health, field groundedness, golden
identity strength, event-type confidence and mean field confidence. Weights and
component sub-scores are returned so the number is auditable, not a black box.
"""

from __future__ import annotations

from statistics import fmean

from app.domain.enums import GoldenMatchStatus, GuardrailStatus, Severity
from app.domain.schemas import (
    DataQualityScore,
    ExtractedField,
    GuardrailResult,
)

_WEIGHTS = {
    "guardrails": 0.30,
    "groundedness": 0.20,
    "identity": 0.20,
    "type_confidence": 0.15,
    "field_confidence": 0.15,
}
_STATUS_SCORE = {
    GuardrailStatus.PASS: 1.0,
    GuardrailStatus.WARN: 0.5,
    GuardrailStatus.FAIL: 0.0,
}
_SEVERITY_WEIGHT = {Severity.INFO: 1.0, Severity.WARNING: 2.0, Severity.CRITICAL: 3.0}
_GOLDEN_SCORE = {
    GoldenMatchStatus.EXACT: 1.0,
    GoldenMatchStatus.PARTIAL: 0.7,
    GoldenMatchStatus.NONE: 0.2,
    GoldenMatchStatus.CONFLICT: 0.0,
}


def _guardrail_component(guardrails: list[GuardrailResult]) -> float:
    scored = [g for g in guardrails if g.status in _STATUS_SCORE]
    if not scored:
        return 1.0
    num = sum(_STATUS_SCORE[g.status] * _SEVERITY_WEIGHT[g.severity] for g in scored)
    den = sum(_SEVERITY_WEIGHT[g.severity] for g in scored)
    return num / den if den else 1.0


def compute_dq_score(
    *,
    guardrails: list[GuardrailResult],
    fields: list[ExtractedField],
    golden_status: GoldenMatchStatus,
    type_confidence: float,
) -> DataQualityScore:
    valued = [f for f in fields if f.value not in (None, "")]
    grounded = fmean([1.0 if f.grounded else 0.0 for f in valued]) if valued else 1.0
    field_conf = fmean([f.confidence.p_correct for f in valued]) if valued else 0.0

    components = {
        "guardrails": _guardrail_component(guardrails),
        "groundedness": grounded,
        "identity": _GOLDEN_SCORE.get(golden_status, 0.0),
        "type_confidence": max(0.0, min(1.0, type_confidence)),
        "field_confidence": max(0.0, min(1.0, field_conf)),
    }
    score = sum(_WEIGHTS[k] * v for k, v in components.items())
    return DataQualityScore(score=round(score, 4), components={k: round(v, 4) for k, v in components.items()})
