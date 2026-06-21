"""Assemble self-consistency consensus into a typed record + audited fields.

Coerces string values into typed record fields, anchors each value in the source
(native bbox provenance, or vision quote for scans) to derive groundedness, and
computes a provisional per-field confidence. The guardrail signal is folded in
afterwards (see :func:`apply_guardrail_signal`).
"""

from __future__ import annotations

from dataclasses import dataclass

from rapidfuzz import fuzz

from app.agent.confidence import fuse_field_confidence
from app.agent.selfconsistency import Consensus, FieldConsensus
from app.config.settings import Settings
from app.domain.enums import EvidenceSource
from app.domain.parsing import parse_br_date, parse_br_decimal, parse_percent
from app.domain.schemas import Evidence, ExtractedField, Record
from app.extraction.pdf import LoadedDocument
from app.extraction.provenance import build_evidence

# raw field name -> Record attribute (None = not a direct record column)
_RECORD_MAP = {
    "emissor": "emissor",
    "cnpj": "cnpj",
    "isin": "isin",
    "ticker": "ticker",
    "data_aprovacao": "data_aprovacao",
    "data_com": "data_com",
    "data_ex": "data_ex",
    "data_pagamento": "data_pagamento",
    "valor": "valor",
    "valor_bruto": "valor_bruto",
    "valor_liquido": "valor_liquido",
    "irrf": "irrf_rate",
    "proporcao": "proporcao",
    "moeda": "moeda",
}
_DATE_ATTRS = {"data_aprovacao", "data_com", "data_ex", "data_pagamento"}
_DECIMAL_ATTRS = {"valor", "valor_bruto", "valor_liquido"}


@dataclass
class FieldSignals:
    """Raw fusion signals kept so confidence can be recomputed after guardrails."""

    name: str
    agreement: float
    self_report: float
    groundedness: float


def _coerce(attr: str, value: str | None):
    if value is None:
        return None
    if attr in _DATE_ATTRS:
        return parse_br_date(value)
    if attr in _DECIMAL_ATTRS:
        return parse_br_decimal(value)
    if attr == "irrf_rate":
        return parse_percent(value)
    if attr in {"isin", "ticker"}:
        return value.strip().upper()
    return value.strip()


def _evidence_for(
    fc: FieldConsensus, doc: LoadedDocument, settings: Settings
) -> tuple[Evidence | None, float]:
    if doc.doc_class.name == "SCANNED":
        if not fc.value:
            return None, 0.0
        score = fuzz.partial_ratio(fc.value.lower(), (fc.quote or "").lower()) / 100.0 if fc.quote else 0.5
        return (
            Evidence(source=EvidenceSource.VISION, quote=fc.quote, page=fc.page,
                     match_score=round(score, 4)),
            score,
        )
    return build_evidence(fc.value, fc.quote, doc)


def assemble(
    consensus: Consensus, doc: LoadedDocument, settings: Settings
) -> tuple[Record, list[ExtractedField], list[FieldSignals]]:
    record_kwargs: dict = {"tipo_evento": consensus.event_type.argmax}
    fields: list[ExtractedField] = []
    signals: list[FieldSignals] = []

    for fc in consensus.fields:
        attr = _RECORD_MAP.get(fc.name)
        typed = _coerce(attr, fc.value) if attr else fc.value
        if attr and typed is not None:
            record_kwargs[attr] = typed

        evidence, ground_score = _evidence_for(fc, doc, settings)
        grounded = bool(fc.value) and ground_score >= settings.groundedness_min_score

        confidence = fuse_field_confidence(
            agreement=fc.agreement,
            self_report=fc.self_report,
            groundedness=ground_score,
            guardrail_ok=1.0,
        )
        rationale = _rationale(fc, grounded, typed)
        fields.append(
            ExtractedField(
                name=fc.name, value=fc.value, confidence=confidence,
                evidence=evidence, grounded=grounded, rationale=rationale,
            )
        )
        signals.append(FieldSignals(fc.name, fc.agreement, fc.self_report, ground_score))

    record_kwargs.setdefault("moeda", "BRL")
    return Record(**record_kwargs), fields, signals


def _rationale(fc: FieldConsensus, grounded: bool, typed) -> str:
    bits = [f"concordância {fc.agreement:.0%} em {fc.n_present} amostra(s)"]
    bits.append("ancorado na fonte" if grounded else "sem âncora forte na fonte")
    if fc.value and typed is None and fc.name in _RECORD_MAP:
        bits.append("valor não parseável para tipo esperado")
    return "; ".join(bits)


def apply_guardrail_signal(
    fields: list[ExtractedField],
    signals: list[FieldSignals],
    failed_field_names: set[str],
) -> list[ExtractedField]:
    """Recompute confidence for fields named in failing guardrails."""
    by_name = {s.name: s for s in signals}
    out: list[ExtractedField] = []
    for f in fields:
        if f.name in failed_field_names and f.name in by_name:
            s = by_name[f.name]
            f.confidence = fuse_field_confidence(
                agreement=s.agreement, self_report=s.self_report,
                groundedness=s.groundedness, guardrail_ok=0.0,
            )
        out.append(f)
    return out
