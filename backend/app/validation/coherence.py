"""Coherence guardrails (Data Quality checks) over a typed record.

These are the "regras de coerência" the case asks for: date ordering, gross/net
consistency for withholding events, and completeness of required fields. They are
**data-driven** (e.g. the JCP check uses the *extracted* IRRF rate, not a
hard-coded 15%) because the 2026 batch uses a 17.5% rate.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.domain.enums import EventType, GuardrailStatus, Severity
from app.domain.schemas import GuardrailResult, Record

# Required fields per event family (the "conforme o caso" minimum set).
_ALWAYS_REQUIRED = ["emissor", "isin", "ticker", "tipo_evento", "moeda"]
_CASH_REQUIRED = ["data_com", "data_ex", "data_pagamento"]
_RATIO_REQUIRED = ["proporcao"]


def check_date_order(record: Record) -> GuardrailResult:
    """aprovacao <= com < ex <= pagamento (only present pairs are checked)."""
    seq: list[tuple[str, date]] = [
        (name, getattr(record, name))
        for name in ("data_aprovacao", "data_com", "data_ex", "data_pagamento")
        if getattr(record, name) is not None
    ]
    violations: list[str] = []
    for (na, da), (nb, db) in zip(seq, seq[1:], strict=False):
        # com must be strictly before ex; other adjacent pairs allow equality
        strict = na == "data_com" and nb == "data_ex"
        if (da > db) or (strict and da >= db):
            violations.append(f"{na} ({da.isoformat()}) deve preceder {nb} ({db.isoformat()})")

    if violations:
        return GuardrailResult(
            name="date_order",
            status=GuardrailStatus.FAIL,
            severity=Severity.CRITICAL,
            message="; ".join(violations),
            fields=[n for n, _ in seq],
        )
    if len(seq) < 2:
        return GuardrailResult(
            name="date_order",
            status=GuardrailStatus.NA,
            message="datas insuficientes para checar ordem",
        )
    return GuardrailResult(
        name="date_order", status=GuardrailStatus.PASS, message="datas em ordem coerente"
    )


# Typical IRRF band for JCP (15% histórico; 17,5% a partir de 2026) — usado para
# validar a retenção *implícita* quando a alíquota não vem extraída do aviso.
_JCP_IRRF_TYPICAL_MIN = Decimal("0.10")
_JCP_IRRF_TYPICAL_MAX = Decimal("0.20")


def check_jcp_gross_net(record: Record, *, tolerance: Decimal) -> GuardrailResult:
    """Consistência bruto/líquido de um JCP.

    Se a alíquota de IRRF foi extraída, confere líquido ≈ bruto × (1 − alíquota).
    Caso contrário, *infere* a retenção implícita (1 − líquido/bruto) e valida que
    é plausível para um JCP — robusto mesmo quando o provider não extrai a alíquota.
    """
    if record.tipo_evento is not EventType.JCP:
        return GuardrailResult(name="jcp_gross_net", status=GuardrailStatus.NA, message="não é JCP")

    bruto, liquido = record.valor_bruto, record.valor_liquido
    if bruto is None or liquido is None:
        return GuardrailResult(
            name="jcp_gross_net", status=GuardrailStatus.WARN, severity=Severity.WARNING,
            message="JCP sem valor bruto e/ou líquido para conferir retenção",
            fields=["valor_bruto", "valor_liquido"],
        )
    if bruto <= 0:
        return GuardrailResult(
            name="jcp_gross_net", status=GuardrailStatus.WARN, severity=Severity.WARNING,
            message="valor bruto inválido", fields=["valor_bruto"],
        )
    if liquido > bruto:
        return GuardrailResult(
            name="jcp_gross_net", status=GuardrailStatus.FAIL, severity=Severity.CRITICAL,
            message=f"líquido ({liquido}) não pode exceder o bruto ({bruto})",
            fields=["valor_bruto", "valor_liquido"],
        )

    implied = Decimal(1) - (liquido / bruto)

    if record.irrf_rate is not None:
        expected = bruto * (Decimal(1) - record.irrf_rate)
        rel_err = abs(liquido - expected) / expected if expected else Decimal(0)
        if rel_err <= tolerance:
            return GuardrailResult(
                name="jcp_gross_net", status=GuardrailStatus.PASS,
                message=f"líquido coerente com IRRF informado de {record.irrf_rate:.2%} (erro {rel_err:.2%})",
                fields=["valor_bruto", "valor_liquido", "irrf_rate"],
            )
        return GuardrailResult(
            name="jcp_gross_net", status=GuardrailStatus.FAIL, severity=Severity.CRITICAL,
            message=(
                f"líquido {liquido} ≠ esperado {expected:.10f} "
                f"(bruto × (1−{record.irrf_rate:.2%})); retenção implícita {implied:.2%}"
            ),
            fields=["valor_bruto", "valor_liquido", "irrf_rate"],
        )

    # alíquota não extraída -> validar a retenção implícita
    if _JCP_IRRF_TYPICAL_MIN <= implied <= _JCP_IRRF_TYPICAL_MAX:
        return GuardrailResult(
            name="jcp_gross_net", status=GuardrailStatus.PASS,
            message=f"retenção implícita {implied:.2%} compatível com IRRF de JCP (alíquota não informada no aviso)",
            fields=["valor_bruto", "valor_liquido"],
        )
    return GuardrailResult(
        name="jcp_gross_net", status=GuardrailStatus.WARN, severity=Severity.WARNING,
        message=f"retenção implícita {implied:.2%} atípica para JCP; confirmar alíquota e valores",
        fields=["valor_bruto", "valor_liquido"],
    )


def check_event_type_substance(record: Record) -> GuardrailResult:
    """Catch the dividendo↔JCP trap by economic substance.

    A "dividendo" that withholds tax to yield a net per-share value (líquido <
    bruto) is structurally a JCP (remuneração sobre capital próprio). Tax/
    operational treatment differs, so we flag the likely misclassification.
    """
    if (
        record.tipo_evento is EventType.DIVIDENDO
        and record.valor_bruto is not None
        and record.valor_liquido is not None
        and record.valor_liquido < record.valor_bruto
    ):
        return GuardrailResult(
            name="event_type_substance",
            status=GuardrailStatus.FAIL,
            severity=Severity.CRITICAL,
            message=(
                "classificado como dividendo, mas há retenção na fonte (líquido < bruto) — "
                "substância compatível com JCP; confirmar tipo e tratamento tributário"
            ),
            fields=["tipo_evento", "valor_liquido"],
        )
    return GuardrailResult(
        name="event_type_substance",
        status=GuardrailStatus.NA,
        message="sem indício de inconsistência entre tipo e substância",
    )


def check_required_fields(record: Record) -> GuardrailResult:
    """Completeness of the minimum field set, conditioned on event family."""
    required = list(_ALWAYS_REQUIRED)
    etype = record.tipo_evento
    if etype and etype.is_cash_provento:
        required += _CASH_REQUIRED
        if record.valor is None and record.valor_bruto is None:
            required.append("valor")
    elif etype and etype.is_share_ratio_event:
        required += _RATIO_REQUIRED

    missing = [f for f in required if getattr(record, f, None) in (None, "")]
    if not missing:
        return GuardrailResult(
            name="required_fields", status=GuardrailStatus.PASS, message="campos mínimos presentes"
        )
    return GuardrailResult(
        name="required_fields",
        status=GuardrailStatus.FAIL,
        severity=Severity.WARNING,
        message=f"campos obrigatórios ausentes: {', '.join(missing)}",
        fields=missing,
    )
