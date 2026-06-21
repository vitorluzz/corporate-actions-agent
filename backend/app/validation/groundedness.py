"""Groundedness guardrail (anti-hallucination).

A value the system cannot anchor to the source is the dangerous case the brief
warns about ("valores inventados viram prejuízo"). Identity and monetary fields
that are present but ungrounded are escalated; soft fields only warn.
"""

from __future__ import annotations

from app.domain.enums import GuardrailStatus, Severity
from app.domain.schemas import ExtractedField, GuardrailResult

_CRITICAL_FIELDS = frozenset(
    {"isin", "ticker", "valor", "valor_bruto", "valor_liquido", "data_pagamento"}
)


def check_groundedness(fields: list[ExtractedField]) -> GuardrailResult:
    ungrounded = [f.name for f in fields if f.value not in (None, "") and not f.grounded]
    if not ungrounded:
        return GuardrailResult(
            name="groundedness",
            status=GuardrailStatus.PASS,
            message="todos os valores extraídos estão ancorados na fonte",
        )
    critical = [n for n in ungrounded if n in _CRITICAL_FIELDS]
    return GuardrailResult(
        name="groundedness",
        status=GuardrailStatus.FAIL if critical else GuardrailStatus.WARN,
        severity=Severity.CRITICAL if critical else Severity.WARNING,
        message=(
            "valores sem âncora na fonte (possível alucinação): "
            + ", ".join(ungrounded)
        ),
        fields=ungrounded,
    )
