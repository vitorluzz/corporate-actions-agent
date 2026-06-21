"""Deterministic, justified routing: AUTO_APPROVE | HUMAN_REVIEW | REJECT.

Every decision carries human-readable reasons and concrete required actions, so
the operator knows *what* to do and *why* — and an auditor can replay the logic.
"""

from __future__ import annotations

from app.config.settings import Settings
from app.domain.enums import (
    GoldenMatchStatus,
    GuardrailStatus,
    RoutingDecision,
    Severity,
)
from app.domain.schemas import (
    DataQualityScore,
    EventTypeDistribution,
    ExtractedField,
    GoldenMatch,
    GuardrailResult,
    Record,
    Routing,
)


def _dedup(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for it in items:
        if it not in seen:
            seen.add(it)
            out.append(it)
    return out


def decide_routing(
    *,
    record: Record,
    fields: list[ExtractedField],
    event_type: EventTypeDistribution,
    guardrails: list[GuardrailResult],
    golden_match: GoldenMatch,
    dq: DataQualityScore,
    settings: Settings,
    is_scanned: bool,
) -> Routing:
    # -- REJECT (identity untrustworthy) ------------------------------------
    if golden_match.status is GoldenMatchStatus.CONFLICT:
        return Routing(
            decision=RoutingDecision.REJECT,
            reasons=["identificadores apontam para emissores distintos na base"],
            required_human_actions=["resolver conflito de identidade antes de processar"],
        )
    # A scanned doc that couldn't be read is never auto-rejected — a human must look.
    if golden_match.status is GoldenMatchStatus.NONE and not record.isin and not is_scanned:
        return Routing(
            decision=RoutingDecision.REJECT,
            reasons=["identidade não reconhecível (sem ISIN e fora da base de referência)"],
            required_human_actions=["identificar o emissor manualmente"],
        )

    reasons: list[str] = []
    actions: list[str] = []

    if golden_match.status is GoldenMatchStatus.NONE and not (is_scanned and not record.isin):
        reasons.append("emissor desconhecido (fora da base de referência)")
        actions.append("cadastrar/validar o emissor na base de referência")
    elif golden_match.status is GoldenMatchStatus.PARTIAL and golden_match.discrepancies:
        diverged = ", ".join(d.field for d in golden_match.discrepancies)
        reasons.append(f"divergência com a base de referência em: {diverged}")
        actions.append("conferir identificadores divergentes")

    if event_type.argmax.is_ambiguous:
        reasons.append(f"tipo de evento ambíguo/genérico ({event_type.argmax.value})")
        actions.append("classificar o tipo de evento manualmente")
    if event_type.entropy > settings.type_entropy_review_threshold:
        reasons.append(f"alta incerteza na classificação do tipo (entropia {event_type.entropy:.2f})")

    for g in guardrails:
        if g.status is GuardrailStatus.FAIL and g.severity is Severity.CRITICAL:
            reasons.append(f"falha de coerência: {g.name} — {g.message}")
            actions.append(f"corrigir/validar: {g.name}")

    req = next((g for g in guardrails if g.name == "required_fields" and g.status is GuardrailStatus.FAIL), None)
    if req:
        reasons.append("campos obrigatórios ausentes")
        actions.append("preencher campos: " + ", ".join(req.fields))

    low = [
        f.name for f in fields
        if f.value not in (None, "") and f.confidence.p_correct < settings.field_review_threshold
    ]
    if low:
        reasons.append("campos de baixa confiança: " + ", ".join(low))
        actions.append("revisar campos: " + ", ".join(low))

    if is_scanned:
        if not record.isin:
            reasons.append(
                "documento escaneado não pôde ser lido automaticamente "
                "(sem camada de texto; requer visão/OCR ou leitura humana)"
            )
            actions.append("ler o documento manualmente ou reprocessar com visão (Gemini)")
        else:
            reasons.append("documento escaneado — extração por visão; conferir a leitura")
            actions.append("validar valores contra a imagem")

    if dq.score < settings.dq_review_threshold:
        reasons.append(f"Data Quality abaixo do limiar ({dq.score:.2f} < {settings.dq_review_threshold:.2f})")

    if reasons:
        return Routing(
            decision=RoutingDecision.HUMAN_REVIEW,
            reasons=_dedup(reasons),
            required_human_actions=_dedup(actions),
        )

    return Routing(
        decision=RoutingDecision.AUTO_APPROVE,
        reasons=["todos os guardrails passaram; identidade confirmada e campos confiáveis"],
        required_human_actions=[],
    )
