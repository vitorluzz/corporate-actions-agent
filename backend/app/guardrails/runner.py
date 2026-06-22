"""Guardrail runner — composes all deterministic checks into one list.

ISIN/CNPJ check digits are reported as **advisory** (INFO severity): on this
synthetic batch the identifiers are fictitious, so the golden base is the
authoritative identity oracle. ticker↔class and the coherence rules are
authoritative.
"""

from __future__ import annotations

from decimal import Decimal

from app.config.settings import Settings
from app.domain.enums import GuardrailStatus, Severity
from app.domain.schemas import ExtractedField, GuardrailResult, Record
from app.validation.coherence import (
    check_date_order,
    check_event_type_substance,
    check_jcp_gross_net,
    check_required_fields,
)
from app.validation.groundedness import check_groundedness
from app.validation.identifiers import (
    cnpj_is_valid,
    isin_is_valid,
    ticker_class_consistent,
)


def _isin_checksum(record: Record) -> GuardrailResult:
    if not record.isin:
        return GuardrailResult(name="isin_checksum", status=GuardrailStatus.NA, message="sem ISIN")
    ok = isin_is_valid(record.isin)
    return GuardrailResult(
        name="isin_checksum",
        status=GuardrailStatus.PASS if ok else GuardrailStatus.WARN,
        severity=Severity.INFO,
        message="dígito verificador OK" if ok else "dígito verificador inválido (advisório; identidade pela base)",
        fields=["isin"],
    )


def _cnpj_checksum(record: Record) -> GuardrailResult:
    if not record.cnpj:
        return GuardrailResult(name="cnpj_checksum", status=GuardrailStatus.NA, message="sem CNPJ")
    ok = cnpj_is_valid(record.cnpj)
    return GuardrailResult(
        name="cnpj_checksum",
        status=GuardrailStatus.PASS if ok else GuardrailStatus.WARN,
        severity=Severity.INFO,
        message="dígito verificador OK" if ok else "dígito verificador inválido (advisório)",
        fields=["cnpj"],
    )


def _ticker_class(record: Record) -> GuardrailResult:
    if not record.ticker:
        return GuardrailResult(name="ticker_class", status=GuardrailStatus.NA, message="sem ticker")
    # We don't have a declared class on the record; cross-check against golden later.
    expected = ticker_class_consistent(record.ticker, None)[1]
    return GuardrailResult(
        name="ticker_class",
        status=GuardrailStatus.PASS if expected else GuardrailStatus.WARN,
        severity=Severity.INFO,
        message=f"sufixo do ticker indica classe {expected.value}" if expected else "sufixo de ticker não reconhecido",
        fields=["ticker"],
    )


def run_guardrails(
    record: Record, fields: list[ExtractedField], settings: Settings
) -> list[GuardrailResult]:
    return [
        _isin_checksum(record),
        _cnpj_checksum(record),
        _ticker_class(record),
        check_required_fields(record),
        check_date_order(record),
        check_event_type_substance(record),
        check_jcp_gross_net(
            record,
            tolerance=Decimal(str(settings.jcp_net_tolerance)),
        ),
        check_groundedness(fields),
    ]
