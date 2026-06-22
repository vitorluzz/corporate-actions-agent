"""P1c tests: cross-modal fusion (Gemini Vision × Tesseract OCR vote)."""

from __future__ import annotations

from app.agent.crossmodal import (
    CrossModal,
    crosscheck_guardrail,
    crossmodal_map,
)
from app.agent.selfconsistency import aggregate
from app.domain.enums import GuardrailStatus, Severity
from app.llm.base import RawExtraction, RawField


def _consensus(**fields: str | None):
    return aggregate([RawExtraction(fields=[RawField(name=k, value=v) for k, v in fields.items()])])


def test_dates_agree_across_formats() -> None:
    # vision emits ISO, OCR-heuristic emits BR — type-aware canon makes them agree
    vision = _consensus(data_pagamento="2026-08-21", valor_bruto="0.1124300000")
    ocr = _consensus(data_pagamento="21/08/2026", valor_bruto="R$ 0,1124300000")
    cm = crossmodal_map(vision, ocr, "data de pagamento 21/08/2026 valor bruto 0,11243")
    assert cm["data_pagamento"].agree is True
    assert cm["valor_bruto"].agree is True
    assert crosscheck_guardrail(cm).status is GuardrailStatus.PASS


def test_disagreement_on_critical_field_fails_critical() -> None:
    vision = _consensus(data_pagamento="2026-08-21")
    ocr = _consensus(data_pagamento="2026-09-30")
    cm = crossmodal_map(vision, ocr, "...")
    assert cm["data_pagamento"].disagrees is True
    g = crosscheck_guardrail(cm)
    assert g.status is GuardrailStatus.FAIL
    assert g.severity is Severity.CRITICAL
    assert "data_pagamento" in g.fields


def test_presence_confirmation_without_ocr_field() -> None:
    # OCR-heuristic didn't extract the field, but the value is present in OCR text
    vision = _consensus(emissor="TELECOM NORTE PARTICIPAÇÕES S.A.")
    ocr = _consensus()  # no fields
    cm = crossmodal_map(vision, ocr, "aviso da TELECOM NORTE PARTICIPAÇÕES S.A. ...")
    assert cm["emissor"].confirmed is True
    assert cm["emissor"].agree is False  # no OCR counterpart to agree with
    # no disagreement (ocr_value is None) → guardrail passes
    assert crosscheck_guardrail(cm).status is GuardrailStatus.PASS


def test_empty_map_passes() -> None:
    g = crosscheck_guardrail({})
    assert g.status is GuardrailStatus.PASS


def test_crossmodal_dataclass_disagrees_property() -> None:
    assert CrossModal("x", "A", "B", agree=False, confirmed=False).disagrees is True
    assert CrossModal("x", "A", None, agree=False, confirmed=True).disagrees is False
    assert CrossModal("x", None, "B", agree=False, confirmed=False).disagrees is False
