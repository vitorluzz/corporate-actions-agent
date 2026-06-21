"""Deterministic validators exposed as LangChain tools (function calling).

The graph invokes these tools deterministically in the guardrail node — because
validation must be *guaranteed* to run, not left to model discretion — but they
are genuine ``StructuredTool``s and can be bound to the LLM for agentic calling.
Each tool is a thin wrapper over a pure function in ``app.validation``.
"""

from __future__ import annotations

from langchain_core.tools import StructuredTool, tool

from app.domain.golden import GoldenBase
from app.validation.identifiers import (
    cnpj_is_valid,
    expected_class_for_ticker,
    isin_is_valid,
    ticker_class_consistent,
)


@tool
def validate_isin(isin: str) -> dict:
    """Valida o dígito verificador (mod-10) de um código ISIN."""
    return {"isin": isin, "valid": isin_is_valid(isin)}


@tool
def validate_cnpj(cnpj: str) -> dict:
    """Valida os dígitos verificadores (mod-11) de um CNPJ."""
    return {"cnpj": cnpj, "valid": cnpj_is_valid(cnpj)}


@tool
def validate_ticker_class(ticker: str, classe: str | None = None) -> dict:
    """Confere o sufixo do ticker (3=ON, 4=PN, 11=Unit) contra a classe declarada."""
    ok, expected = ticker_class_consistent(ticker, classe)
    return {
        "ticker": ticker,
        "consistent": ok,
        "expected_class": expected.value if expected else None,
    }


@tool
def check_jcp_gross_net(bruto: float, liquido: float, irrf_rate: float = 0.175) -> dict:
    """Confere se o valor líquido ≈ bruto × (1 − IRRF) para um JCP."""
    expected = bruto * (1 - irrf_rate)
    rel_err = abs(liquido - expected) / expected if expected else 0.0
    return {"expected_liquido": expected, "rel_error": rel_err, "consistent": rel_err <= 0.02}


def make_golden_lookup(golden: GoldenBase) -> StructuredTool:
    """Build the golden-record lookup tool bound to a specific reference base."""

    @tool
    def lookup_golden_record(
        isin: str | None = None,
        ticker: str | None = None,
        cnpj: str | None = None,
        emissor: str | None = None,
    ) -> dict:
        """Procura um emissor na base de referência por ISIN, ticker, CNPJ ou nome."""
        rec = golden.by_isin(isin) or golden.by_ticker(ticker) or golden.by_cnpj(cnpj)
        score = 1.0
        if rec is None and emissor:
            rec, score = golden.fuzzy_issuer(emissor)
        if rec is None:
            return {"found": False}
        return {
            "found": True,
            "emissor": rec.emissor,
            "isin": rec.isin,
            "ticker": rec.ticker,
            "classe": rec.classe,
            "match_score": round(score, 3),
        }

    return lookup_golden_record


def build_toolset(golden: GoldenBase) -> list[StructuredTool]:
    return [
        validate_isin,
        validate_cnpj,
        validate_ticker_class,
        check_jcp_gross_net,
        make_golden_lookup(golden),
    ]


__all__ = [
    "validate_isin",
    "validate_cnpj",
    "validate_ticker_class",
    "check_jcp_gross_net",
    "make_golden_lookup",
    "build_toolset",
    "expected_class_for_ticker",
]
