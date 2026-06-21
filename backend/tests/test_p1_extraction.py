"""P1 tests: BR parsing (pure) + extraction/provenance (integration on real PDFs)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.config import get_settings
from app.domain.parsing import parse_br_date, parse_br_decimal, parse_percent
from app.extraction import build_evidence, load_document
from app.extraction.pdf import DocumentClass

DOCS = get_settings().documents_dir


# -- pure parsing -----------------------------------------------------------
def test_parse_br_date_formats() -> None:
    assert parse_br_date("10/07/2026") == date(2026, 7, 10)
    assert parse_br_date("2026-07-10") == date(2026, 7, 10)
    assert parse_br_date("A definir (vide aviso complementar)") is None
    assert parse_br_date("31/02/2026") is None  # invalid calendar date
    assert parse_br_date(None) is None


def test_parse_br_decimal_and_percent() -> None:
    assert parse_br_decimal("R$ 0,1738420000") == Decimal("0.1738420000")
    assert parse_br_decimal("1.234,56") == Decimal("1234.56")
    assert parse_percent("17,5%") == Decimal("0.175")
    assert parse_br_decimal("") is None


# -- extraction integration -------------------------------------------------
@pytest.mark.skipif(not DOCS.exists(), reason="document batch not present")
def test_scanned_detection() -> None:
    scan = load_document(DOCS / "07_telecom_norte_jcp_SCAN.pdf")
    assert scan.doc_class is DocumentClass.SCANNED
    assert scan.images_b64, "scanned doc must render a page image for vision"

    native = load_document(DOCS / "01_energetica_vale_tiete_dividendo.pdf")
    assert native.doc_class is DocumentClass.NATIVE
    assert len(native.full_text) > 500


@pytest.mark.skipif(not DOCS.exists(), reason="document batch not present")
def test_provenance_locates_isin_with_bbox() -> None:
    doc = load_document(DOCS / "01_energetica_vale_tiete_dividendo.pdf")
    evidence, score = build_evidence("BRTIETACNOR3", None, doc)
    assert evidence is not None
    assert score >= 0.9
    assert evidence.bbox is not None
    assert evidence.page == 1
