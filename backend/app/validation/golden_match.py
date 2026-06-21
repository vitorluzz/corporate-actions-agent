"""Explainable entity resolution against the golden reference base.

Resolves a record's identity using ISIN / ticker / CNPJ (exact) and issuer
(fuzzy), then explains *why* it matched or diverged — so an operator can trust
the link without re-checking the base by hand. Conflicting identifiers
(pointing at different golden rows) are surfaced rather than silently resolved.
"""

from __future__ import annotations

from app.domain.enums import GoldenMatchStatus
from app.domain.golden import GoldenBase, GoldenRecord
from app.domain.schemas import Discrepancy, GoldenMatch, Record


def resolve_identity(record: Record, golden: GoldenBase) -> GoldenMatch:
    sources: dict[str, GoldenRecord | None] = {
        "isin": golden.by_isin(record.isin),
        "ticker": golden.by_ticker(record.ticker),
        "cnpj": golden.by_cnpj(record.cnpj),
    }
    fuzzy, fuzzy_score = golden.fuzzy_issuer(record.emissor)
    if fuzzy is not None:
        sources["emissor"] = fuzzy

    found = {k: v for k, v in sources.items() if v is not None}

    if not found:
        return GoldenMatch(
            status=GoldenMatchStatus.NONE,
            explanation=(
                "Nenhum identificador (ISIN/ticker/CNPJ/emissor) encontrado na base "
                "de referência — emissor desconhecido. Requer cadastro/validação humana."
            ),
        )

    distinct = {v.isin for v in found.values()}
    if len(distinct) > 1:
        pointers = ", ".join(f"{k}→{v.ticker}" for k, v in found.items())
        return GoldenMatch(
            status=GoldenMatchStatus.CONFLICT,
            matched_on=list(found.keys()),
            explanation=f"Identificadores apontam para emissores distintos ({pointers}).",
        )

    target = next(iter(found.values()))
    matched_on = list(found.keys())

    discrepancies: list[Discrepancy] = []
    if record.isin and record.isin.strip().upper() != target.isin:
        discrepancies.append(Discrepancy(field="isin", extracted=record.isin,
                                         reference=target.isin, note="ISIN diverge da base"))
    if record.ticker and record.ticker.strip().upper() != target.ticker:
        discrepancies.append(Discrepancy(field="ticker", extracted=record.ticker,
                                         reference=target.ticker, note="ticker diverge da base"))

    has_strong = bool(sources["isin"] or sources["ticker"])
    status = (
        GoldenMatchStatus.EXACT
        if (sources["isin"] and sources["ticker"] and not discrepancies)
        else GoldenMatchStatus.PARTIAL
    )

    parts = [f"casou por {', '.join(matched_on)} → {target.emissor} ({target.ticker})"]
    if "emissor" in found and fuzzy_score < 1.0:
        parts.append(f"emissor por similaridade {fuzzy_score:.0%}")
    if discrepancies:
        parts.append("divergências: " + "; ".join(d.note for d in discrepancies))
    if not has_strong:
        parts.append("apenas identificadores fracos (sem ISIN/ticker) — confirmar")

    return GoldenMatch(
        status=status,
        matched_on=matched_on,
        discrepancies=discrepancies,
        explanation="; ".join(parts) + ".",
        golden_emissor=target.emissor,
        golden_isin=target.isin,
        golden_ticker=target.ticker,
    )
