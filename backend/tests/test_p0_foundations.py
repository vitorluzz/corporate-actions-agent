"""P0 tests: golden base + data-contract invariants."""

from __future__ import annotations

from app.domain.golden import GoldenBase, normalize_issuer
from app.domain.schemas import Confidence


def test_golden_exact_lookups(golden_base: GoldenBase) -> None:
    rec = golden_base.by_isin("BRTIETACNOR3")
    assert rec is not None
    assert rec.ticker == "TIET3"
    assert golden_base.by_ticker("BMRD4").emissor.startswith("Banco Meridional")
    assert golden_base.by_cnpj("12345678000190").isin == "BRTIETACNOR3"


def test_golden_fuzzy_issuer_handles_accents_and_suffix(golden_base: GoldenBase) -> None:
    rec, score = golden_base.fuzzy_issuer("energetica vale do tiete sa")
    assert rec is not None
    assert rec.ticker == "TIET3"
    assert score >= 0.82


def test_golden_unknown_issuer_returns_none(golden_base: GoldenBase) -> None:
    rec, _ = golden_base.fuzzy_issuer("Construtora Horizonte S.A.")
    assert rec is None


def test_normalize_issuer_strips_corporate_suffix() -> None:
    assert normalize_issuer("Telecom Norte Participações S.A.") == "telecom norte"


def test_confidence_normalizes_to_one() -> None:
    # in-range components that don't sum to 1 are renormalized by the validator
    c = Confidence(p_correct=0.8, p_uncertain=0.4, p_error=0.4)
    assert abs((c.p_correct + c.p_uncertain + c.p_error) - 1.0) < 1e-9
    assert c.p_correct == 0.5


def test_confidence_from_raw_clamps_and_normalizes() -> None:
    c = Confidence.from_raw(2.0, 1.0, 1.0)
    assert c.p_correct == 0.5
    assert abs((c.p_correct + c.p_uncertain + c.p_error) - 1.0) < 1e-9
    # negative raw scores are clamped to zero
    assert Confidence.from_raw(1.0, -5.0, 0.0).p_correct == 1.0


def test_confidence_label_thresholds() -> None:
    assert Confidence(p_correct=0.9, p_uncertain=0.05, p_error=0.05).label.value == "HIGH"
    assert Confidence(p_correct=0.6, p_uncertain=0.3, p_error=0.1).label.value == "MEDIUM"
    assert Confidence(p_correct=0.2, p_uncertain=0.3, p_error=0.5).label.value == "LOW"
