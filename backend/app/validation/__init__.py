"""Validation layer: pure validators, coherence rules, entity resolution, DQ."""

from app.validation.coherence import (
    check_date_order,
    check_event_type_substance,
    check_jcp_gross_net,
    check_required_fields,
)
from app.validation.dq import compute_dq_score
from app.validation.golden_match import resolve_identity
from app.validation.groundedness import check_groundedness
from app.validation.identifiers import (
    cnpj_is_valid,
    expected_class_for_ticker,
    isin_is_valid,
    ticker_class_consistent,
)

__all__ = [
    "check_date_order",
    "check_event_type_substance",
    "check_jcp_gross_net",
    "check_required_fields",
    "compute_dq_score",
    "resolve_identity",
    "check_groundedness",
    "cnpj_is_valid",
    "isin_is_valid",
    "ticker_class_consistent",
    "expected_class_for_ticker",
]
