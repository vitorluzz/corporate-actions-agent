"""Parsing helpers for Brazilian-format dates and decimals.

Kept deterministic and side-effect free so they are trivially unit-tested and
reused by both the agent (coercing model strings into typed values) and the
guardrails (coherence checks).
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation

_DATE_DMY = re.compile(r"\b(\d{2})/(\d{2})/(\d{4})\b")
_DATE_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_NON_DATE_TOKENS = ("a definir", "oportunamente", "a ser", "complementar")


def parse_br_date(value: str | None) -> date | None:
    """Parse dd/mm/yyyy or yyyy-mm-dd. Non-dates (e.g. 'A definir') -> None."""
    if not value:
        return None
    low = value.strip().lower()
    if any(tok in low for tok in _NON_DATE_TOKENS):
        return None
    m = _DATE_DMY.search(value)
    if m:
        d, mth, y = (int(g) for g in m.groups())
        try:
            return date(y, mth, d)
        except ValueError:
            return None
    m = _DATE_ISO.search(value)
    if m:
        y, mth, d = (int(g) for g in m.groups())
        try:
            return date(y, mth, d)
        except ValueError:
            return None
    return None


def parse_br_decimal(value: str | None) -> Decimal | None:
    """Parse '#R$ 0,1738420000' / '1.234,56' / '0.42' -> Decimal."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    s = s.replace("R$", "").replace("r$", "").strip()
    s = re.sub(r"[^\d.,-]", "", s)
    if not s:
        return None
    if "," in s:
        # BR convention: dot = thousands, comma = decimal
        s = s.replace(".", "").replace(",", ".")
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def parse_percent(value: str | None) -> Decimal | None:
    """Parse '17,5%' -> Decimal('0.175')."""
    if not value:
        return None
    dec = parse_br_decimal(value.replace("%", ""))
    if dec is None:
        return None
    return dec / Decimal(100)
