"""Per-field confidence fusion → ternary ``{p_correct, p_uncertain, p_error}``.

Transparent, documented blend of four signals (mirrors the COBOL PoC's
P(Chave)/P(Valor)/P(Incerto)):
  - s = self-consistency agreement across samples
  - r = model self-reported confidence
  - v = groundedness (value anchored in source)
  - g = guardrail signal for the field (1 pass / 0 fail)

The remaining probability mass is split between *uncertain* (driven by low
agreement) and *error* (driven by low groundedness), so the three components
tell an operator *why* a value is shaky, not just how much.
"""

from __future__ import annotations

from app.domain.schemas import Confidence

# Weights are explicit and documented (auditable, not a black box).
_W_AGREEMENT = 0.35
_W_SELF_REPORT = 0.20
_W_GROUNDEDNESS = 0.30
_W_GUARDRAIL = 0.15


def fuse_field_confidence(
    *,
    agreement: float,
    self_report: float,
    groundedness: float,
    guardrail_ok: float = 1.0,
) -> Confidence:
    s = max(0.0, min(1.0, agreement))
    r = max(0.0, min(1.0, self_report))
    v = max(0.0, min(1.0, groundedness))
    g = max(0.0, min(1.0, guardrail_ok))

    p_correct = _W_AGREEMENT * s + _W_SELF_REPORT * r + _W_GROUNDEDNESS * v + _W_GUARDRAIL * g
    remaining = max(0.0, 1.0 - p_correct)

    err_drive = (1.0 - v) + (1.0 - g)        # ungrounded / failed -> likely wrong
    unc_drive = (1.0 - s) + (1.0 - r)        # unstable / unsure -> uncertain
    total_drive = err_drive + unc_drive
    if total_drive <= 0:
        return Confidence.from_raw(p_correct, 0.0, 0.0)

    p_error = remaining * err_drive / total_drive
    p_uncertain = remaining * unc_drive / total_drive
    return Confidence.from_raw(p_correct, p_uncertain, p_error)
