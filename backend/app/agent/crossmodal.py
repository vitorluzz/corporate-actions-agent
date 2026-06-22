"""Cross-modal fusion for scanned documents (Gemini Vision × Tesseract OCR).

On a scan, two *independent* pipelines read the same page:
  - **Gemini Vision** reads the page image and returns structured values + quotes.
  - **Tesseract OCR** transcribes the image to text; the deterministic stub then
    extracts a second set of values from that text.

Treating them as two votes lets us (a) *anchor* a vision value to the OCR word
box (handled in provenance), (b) *verify* a vision value against the OCR text
(groundedness / anti-hallucination), and (c) flag *disagreements* between the
modalities for human review. This is the "they complement each other" design.
"""

from __future__ import annotations

from dataclasses import dataclass

from rapidfuzz import fuzz

from app.agent.selfconsistency import Consensus, aggregate
from app.config.settings import Settings
from app.domain.enums import GuardrailStatus, Severity
from app.domain.parsing import parse_br_date, parse_br_decimal, parse_percent
from app.domain.schemas import GuardrailResult
from app.extraction.pdf import LoadedDocument
from app.llm.base import ExtractionInput

_DATE_FIELDS = {"data_aprovacao", "data_com", "data_ex", "data_pagamento"}
_DECIMAL_FIELDS = {"valor", "valor_bruto", "valor_liquido"}
# Fields where a vision↔OCR disagreement is materially risky (escalate to review).
_CRITICAL_FIELDS = frozenset(
    {
        "isin", "ticker", "cnpj", "emissor",
        "valor", "valor_bruto", "valor_liquido",
        "data_com", "data_ex", "data_pagamento",
    }
)
_AGREE_FUZZY = 90.0     # string near-equality
_CONFIRM_FUZZY = 85.0   # value present somewhere in the OCR text


@dataclass(frozen=True)
class CrossModal:
    """Per-field comparison between the vision value and the OCR-text value."""

    name: str
    vision_value: str | None
    ocr_value: str | None
    agree: bool        # both modalities present and equal (type-aware)
    confirmed: bool    # vision value appears in the OCR text (presence check)

    @property
    def disagrees(self) -> bool:
        return bool(self.vision_value) and self.ocr_value is not None and not self.agree


def _canon(name: str, value: str | None) -> str | None:
    """Type-aware canonical form so '21/08/2026' == '2026-08-21' etc."""
    if value is None or not value.strip():
        return None
    if name in _DATE_FIELDS:
        d = parse_br_date(value)
        return d.isoformat() if d else value.strip().casefold()
    if name in _DECIMAL_FIELDS:
        d = parse_br_decimal(value)
        return str(d) if d is not None else value.strip().casefold()
    if name == "irrf":
        p = parse_percent(value)
        return str(p) if p is not None else value.strip().casefold()
    return value.strip().casefold()


def _values_agree(name: str, a: str | None, b: str | None) -> bool:
    ca, cb = _canon(name, a), _canon(name, b)
    if ca is None or cb is None:
        return False
    if ca == cb:
        return True
    return fuzz.ratio(ca, cb) >= _AGREE_FUZZY


def _present_in_text(value: str | None, text: str) -> bool:
    if not value or not value.strip():
        return False
    needle = value.strip().casefold()
    haystack = text.casefold()
    if needle in haystack:
        return True
    return fuzz.partial_ratio(needle, haystack) >= _CONFIRM_FUZZY


def build_ocr_consensus(doc: LoadedDocument, settings: Settings) -> Consensus | None:
    """Run the deterministic stub on the OCR text to get an independent vote.

    Returns ``None`` for native docs or scans without a usable OCR text layer.
    """
    if doc.doc_class.name != "SCANNED" or not doc.full_text.strip():
        return None
    # Local import avoids a module cycle (stub ← factory ← agent).
    from app.llm.stub import StubClient

    inp = ExtractionInput(
        doc_id=doc.doc_id, doc_hash=doc.doc_hash, text=doc.full_text, is_scan=False
    )
    sample = StubClient().extract(
        inp, temperature=settings.extraction_temperature, sample_index=0
    )
    return aggregate([sample])


def crossmodal_map(
    vision: Consensus, ocr: Consensus | None, ocr_text: str
) -> dict[str, CrossModal]:
    """Compare each vision field against the OCR-text vote + presence."""
    if ocr is None:
        return {}
    ocr_by = {f.name: f for f in ocr.fields}
    out: dict[str, CrossModal] = {}
    for vf in vision.fields:
        of = ocr_by.get(vf.name)
        ocr_value = of.value if of else None
        agree = bool(vf.value) and _values_agree(vf.name, vf.value, ocr_value)
        confirmed = _present_in_text(vf.value, ocr_text)
        out[vf.name] = CrossModal(vf.name, vf.value, ocr_value, agree, confirmed)
    return out


def crosscheck_guardrail(cms: dict[str, CrossModal]) -> GuardrailResult:
    """Summarize vision↔OCR agreement as an auditable coherence check."""
    disagree = [name for name, cm in cms.items() if cm.disagrees]
    confirmed = [name for name, cm in cms.items() if cm.agree]
    if not disagree:
        return GuardrailResult(
            name="vision_ocr_crosscheck",
            status=GuardrailStatus.PASS,
            severity=Severity.INFO,
            message=(
                f"visão e OCR concordam em {len(confirmed)} campo(s)"
                if confirmed
                else "sem campos comparáveis entre visão e OCR"
            ),
        )
    critical = [n for n in disagree if n in _CRITICAL_FIELDS]
    return GuardrailResult(
        name="vision_ocr_crosscheck",
        status=GuardrailStatus.FAIL if critical else GuardrailStatus.WARN,
        severity=Severity.CRITICAL if critical else Severity.WARNING,
        message="divergência entre visão e OCR em: " + ", ".join(sorted(disagree)),
        fields=disagree,
    )
