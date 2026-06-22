"""Golden-record reference base loader + indexes for entity resolution.

The reference base is tiny (a handful of issuers), so we deliberately use exact +
fuzzy matching over an in-memory index instead of a vector DB / RAG — see README
trade-offs. Indexes by ISIN, ticker, CNPJ (digits-only) and a normalized issuer
name support the explainable entity-resolution step.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path


def normalize_issuer(name: str) -> str:
    """Casefold, strip accents and corporate suffixes for fuzzy issuer matching."""
    if not name:
        return ""
    nfkd = unicodedata.normalize("NFKD", name)
    no_accents = "".join(c for c in nfkd if not unicodedata.combining(c))
    lowered = no_accents.casefold()
    # drop common corporate suffixes / noise
    lowered = re.sub(r"\b(s\.?a\.?|s/a|ltda\.?|participacoes|holding)\b", " ", lowered)
    return re.sub(r"[^a-z0-9]+", " ", lowered).strip()


def digits_only(value: str | None) -> str:
    return re.sub(r"\D", "", value or "")


@dataclass(frozen=True)
class GoldenRecord:
    emissor: str
    cnpj: str
    isin: str
    ticker: str
    classe: str
    segmento_listagem: str
    status: str

    @property
    def cnpj_digits(self) -> str:
        return digits_only(self.cnpj)

    @property
    def issuer_norm(self) -> str:
        return normalize_issuer(self.emissor)


@dataclass
class GoldenBase:
    """In-memory reference base with lookup indexes."""

    records: list[GoldenRecord] = field(default_factory=list)
    _by_isin: dict[str, GoldenRecord] = field(default_factory=dict)
    _by_ticker: dict[str, GoldenRecord] = field(default_factory=dict)
    _by_cnpj: dict[str, GoldenRecord] = field(default_factory=dict)
    _by_issuer_norm: dict[str, GoldenRecord] = field(default_factory=dict)

    @classmethod
    def from_csv(cls, path: str | Path) -> GoldenBase:
        records: list[GoldenRecord] = []
        with open(path, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                records.append(
                    GoldenRecord(
                        emissor=row["emissor"].strip(),
                        cnpj=row["cnpj"].strip(),
                        isin=row["isin"].strip().upper(),
                        ticker=row["ticker"].strip().upper(),
                        classe=row["classe"].strip(),
                        segmento_listagem=row["segmento_listagem"].strip(),
                        status=row["status"].strip(),
                    )
                )
        return cls.from_records(records)

    @classmethod
    def from_records(cls, records: list[GoldenRecord]) -> GoldenBase:
        base = cls(records=records)
        for r in records:
            base._by_isin[r.isin.upper()] = r
            base._by_ticker[r.ticker.upper()] = r
            base._by_cnpj[r.cnpj_digits] = r
            base._by_issuer_norm[r.issuer_norm] = r
        return base

    # -- exact lookups -------------------------------------------------------
    def by_isin(self, isin: str | None) -> GoldenRecord | None:
        return self._by_isin.get((isin or "").strip().upper())

    def by_ticker(self, ticker: str | None) -> GoldenRecord | None:
        return self._by_ticker.get((ticker or "").strip().upper())

    def by_cnpj(self, cnpj: str | None) -> GoldenRecord | None:
        return self._by_cnpj.get(digits_only(cnpj))

    # -- fuzzy issuer --------------------------------------------------------
    def fuzzy_issuer(self, name: str | None, threshold: float = 0.82) -> tuple[GoldenRecord | None, float]:
        """Return the best issuer match and its similarity score [0,1]."""
        if not name:
            return None, 0.0
        try:
            from rapidfuzz import fuzz, process
        except ImportError:  # pragma: no cover - rapidfuzz is a hard dep
            return None, 0.0

        query = normalize_issuer(name)
        if not query:
            return None, 0.0
        if query in self._by_issuer_norm:
            return self._by_issuer_norm[query], 1.0

        choice = process.extractOne(
            query, list(self._by_issuer_norm.keys()), scorer=fuzz.token_sort_ratio
        )
        if not choice:
            return None, 0.0
        matched_key, score, _ = choice
        norm_score = score / 100.0
        if norm_score >= threshold:
            return self._by_issuer_norm[matched_key], norm_score
        return None, norm_score

    def __len__(self) -> int:
        return len(self.records)
