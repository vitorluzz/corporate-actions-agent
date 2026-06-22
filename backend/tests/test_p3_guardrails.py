"""P3 tests: identifier validators, coherence rules, groundedness, entity resolution."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.domain.enums import EventType, GoldenMatchStatus, GuardrailStatus
from app.domain.golden import GoldenBase
from app.domain.schemas import Confidence, ExtractedField, Record
from app.validation.coherence import (
    check_date_order,
    check_jcp_gross_net,
    check_required_fields,
)
from app.validation.golden_match import resolve_identity
from app.validation.groundedness import check_groundedness
from app.validation.identifiers import (
    cnpj_is_valid,
    isin_is_valid,
    ticker_class_consistent,
)

_HI = Confidence(p_correct=0.9, p_uncertain=0.05, p_error=0.05)


def test_isin_checksum_known_vectors() -> None:
    assert isin_is_valid("US0378331005")  # Apple — real, valid
    assert isin_is_valid("BRSGPMACNPR4")  # synthetic one that happens to be valid
    # Calibration: most synthetic golden ISINs do NOT carry a valid check digit,
    # which is exactly why we treat ISIN checksums as advisory (golden = oracle).
    assert not isin_is_valid("BRTIETACNOR3")
    assert not isin_is_valid("NOTANISIN")


def test_cnpj_checksum() -> None:
    assert cnpj_is_valid("11.222.333/0001-81")
    assert not cnpj_is_valid("12.345.678/0001-90")
    assert not cnpj_is_valid("00000000000000")


def test_ticker_class() -> None:
    assert ticker_class_consistent("TIET3", "ON")[0]
    assert ticker_class_consistent("BMRD4", "PN")[0]
    assert not ticker_class_consistent("TIET3", "PN")[0]
    assert ticker_class_consistent("SANB11", "UNIT")[1].value == "UNIT"


def test_date_order_coherent_passes() -> None:
    rec = Record(
        data_aprovacao=date(2026, 5, 28),
        data_com=date(2026, 6, 12),
        data_ex=date(2026, 6, 15),
        data_pagamento=date(2026, 7, 3),
    )
    assert check_date_order(rec).status is GuardrailStatus.PASS


def test_date_order_payment_before_com_fails() -> None:
    # doc 05 pattern: pagamento (10/07) before data com (15/07)
    rec = Record(
        data_aprovacao=date(2026, 6, 1),
        data_com=date(2026, 7, 15),
        data_ex=date(2026, 7, 16),
        data_pagamento=date(2026, 7, 10),
    )
    res = check_date_order(rec)
    assert res.status is GuardrailStatus.FAIL
    assert "data_pagamento" in res.fields


def test_jcp_gross_net_consistent_at_17_5() -> None:
    rec = Record(
        tipo_evento=EventType.JCP,
        valor_bruto=Decimal("0.1738420000"),
        valor_liquido=Decimal("0.1434196500"),
        irrf_rate=Decimal("0.175"),
    )
    assert check_jcp_gross_net(rec, tolerance=Decimal("0.02")).status is GuardrailStatus.PASS


def test_jcp_gross_net_infers_rate_when_absent() -> None:
    # Provider não extraiu a alíquota, mas bruto/líquido implicam ~17,5% -> coerente.
    rec = Record(
        tipo_evento=EventType.JCP,
        valor_bruto=Decimal("0.1738420000"),
        valor_liquido=Decimal("0.1434196500"),
        irrf_rate=None,
    )
    assert check_jcp_gross_net(rec, tolerance=Decimal("0.02")).status is GuardrailStatus.PASS


def test_jcp_gross_net_mismatch_fails() -> None:
    rec = Record(
        tipo_evento=EventType.JCP,
        valor_bruto=Decimal("0.20"),
        valor_liquido=Decimal("0.20"),  # no withholding applied -> inconsistent
        irrf_rate=Decimal("0.175"),
    )
    assert check_jcp_gross_net(rec, tolerance=Decimal("0.02")).status is GuardrailStatus.FAIL


def test_required_fields_flags_missing_payment() -> None:
    rec = Record(
        emissor="X", isin="BRRVBRACNOR9", ticker="RVBR3", moeda="BRL",
        tipo_evento=EventType.JCP, valor_bruto=Decimal("0.205"),
        data_com=date(2026, 6, 23), data_ex=date(2026, 6, 24), data_pagamento=None,
    )
    res = check_required_fields(rec)
    assert res.status is GuardrailStatus.FAIL
    assert "data_pagamento" in res.fields


def test_groundedness_flags_ungrounded_critical_field() -> None:
    fields = [
        ExtractedField(name="isin", value="BRTIETACNOR3", confidence=_HI, grounded=False),
        ExtractedField(name="ticker", value="TIET3", confidence=_HI, grounded=True),
    ]
    res = check_groundedness(fields)
    assert res.status is GuardrailStatus.FAIL
    assert "isin" in res.fields


def test_resolve_identity_exact_and_unknown(full_golden: GoldenBase) -> None:
    exact = resolve_identity(Record(isin="BRTIETACNOR3", ticker="TIET3"), full_golden)
    assert exact.status is GoldenMatchStatus.EXACT
    assert exact.golden_ticker == "TIET3"

    unknown = resolve_identity(
        Record(emissor="Construtora Horizonte S.A.", isin="BRCNHZACNOR5", ticker="CNHZ3"),
        full_golden,
    )
    assert unknown.status is GoldenMatchStatus.NONE
