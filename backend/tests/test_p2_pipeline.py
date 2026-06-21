"""P2/P4 tests: self-consistency, confidence fusion, and the routing matrix."""

from __future__ import annotations

import pytest

from app.agent.confidence import fuse_field_confidence
from app.agent.runner import run_batch
from app.agent.selfconsistency import aggregate, normalized_entropy
from app.config import get_settings
from app.domain.enums import EventType, RoutingDecision
from app.llm.base import RawExtraction, RawField

DOCS = get_settings().documents_dir


def test_normalized_entropy_bounds() -> None:
    assert normalized_entropy([1.0]) == 0.0
    assert normalized_entropy([0.5, 0.5]) == pytest.approx(1.0)
    assert 0.0 < normalized_entropy([0.8, 0.2]) < 1.0


def test_aggregate_agreement_and_distribution() -> None:
    sample = RawExtraction(
        event_type=EventType.JCP,
        fields=[RawField(name="isin", value="BRBMRDACNPR7", confidence=0.9)],
    )
    consensus = aggregate([sample, sample, sample])
    assert consensus.event_type.argmax is EventType.JCP
    assert consensus.event_type.entropy == 0.0
    isin = next(f for f in consensus.fields if f.name == "isin")
    assert isin.agreement == 1.0


def test_aggregate_split_vote_raises_entropy() -> None:
    a = RawExtraction(event_type=EventType.DIVIDENDO)
    b = RawExtraction(event_type=EventType.JCP)
    consensus = aggregate([a, a, b])  # 2/3 vs 1/3
    assert consensus.event_type.argmax is EventType.DIVIDENDO
    assert consensus.event_type.entropy > 0.0


def test_fuse_confidence_grounded_vs_ungrounded() -> None:
    strong = fuse_field_confidence(agreement=1.0, self_report=0.9, groundedness=1.0)
    weak = fuse_field_confidence(agreement=1.0, self_report=0.9, groundedness=0.0)
    assert strong.p_correct > 0.9
    # losing groundedness materially lowers confidence and shifts mass to error
    assert weak.p_correct < strong.p_correct
    assert weak.p_error > strong.p_error
    assert weak.p_correct < 0.70  # below the field review threshold -> flagged


@pytest.mark.skipif(not DOCS.exists(), reason="document batch not present")
def test_routing_matrix_over_batch() -> None:
    results, summary = run_batch()
    by_id = {r.document.id: r for r in results}
    assert summary.total == 8

    expect = {
        "01_energetica_vale_tiete_dividendo": (RoutingDecision.AUTO_APPROVE, EventType.DIVIDENDO),
        "02_banco_meridional_jcp": (RoutingDecision.AUTO_APPROVE, EventType.JCP),
        "06_petroquimica_litoral_grupamento": (RoutingDecision.AUTO_APPROVE, EventType.GRUPAMENTO),
    }
    for doc_id, (decision, etype) in expect.items():
        assert by_id[doc_id].routing.decision is decision, doc_id
        assert by_id[doc_id].event_type.argmax is etype, doc_id

    # edge cases must all be escalated (never silently auto-approved)
    for doc_id in (
        "03_siderurgica_paranaense_proventos",   # JCP-trap (substance)
        "04_rede_varejo_jcp_sem_data",           # missing payment date
        "05_aurora_saneamento_dividendo_datas",  # date incoherence
        "07_telecom_norte_jcp_SCAN",             # scanned
        "08_construtora_horizonte_bonificacao",  # unknown issuer
    ):
        assert by_id[doc_id].routing.decision is not RoutingDecision.AUTO_APPROVE, doc_id
        assert by_id[doc_id].routing.reasons

    # doc 05 specifically must cite the date-order coherence failure
    assert any("date_order" in r for r in by_id["05_aurora_saneamento_dividendo_datas"].routing.reasons)
