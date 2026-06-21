"""Deterministic identifier validators (ISIN, CNPJ, ticker↔class).

Pure functions — trivially unit-tested and also exposed as LLM tools. See README:
because the batch uses *fictitious* identifiers, ISIN/CNPJ check digits are
treated as **advisory** signals; the golden base is the authoritative identity
oracle. In production with real identifiers we'd escalate a checksum failure.
"""

from __future__ import annotations

import re

from app.domain.enums import ShareClass

_ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")


def _char_to_digits(c: str) -> str:
    """A->10 ... Z->35; digits unchanged (ISIN convention)."""
    if c.isdigit():
        return c
    return str(ord(c) - ord("A") + 10)


def isin_check_digit(isin_body: str) -> int:
    """Luhn (mod-10) check digit over the first 11 ISIN characters."""
    digits = "".join(_char_to_digits(c) for c in isin_body)
    total = 0
    # double every second digit starting from the rightmost
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return (10 - (total % 10)) % 10


def isin_is_valid(isin: str | None) -> bool:
    if not isin:
        return False
    isin = isin.strip().upper()
    if not _ISIN_RE.match(isin):
        return False
    return isin_check_digit(isin[:11]) == int(isin[11])


def cnpj_is_valid(cnpj: str | None) -> bool:
    if not cnpj:
        return False
    nums = re.sub(r"\D", "", cnpj)
    if len(nums) != 14 or len(set(nums)) == 1:
        return False

    def _dv(base: str, weights: list[int]) -> int:
        s = sum(int(d) * w for d, w in zip(base, weights, strict=True))
        r = s % 11
        return 0 if r < 2 else 11 - r

    w1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    w2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    return _dv(nums[:12], w1) == int(nums[12]) and _dv(nums[:13], w2) == int(nums[13])


def expected_class_for_ticker(ticker: str | None) -> ShareClass | None:
    """Infer share class from the ticker's numeric suffix (B3 convention)."""
    if not ticker:
        return None
    m = re.match(r"^[A-Z]{4}(\d{1,2})$", ticker.strip().upper())
    if not m:
        return None
    suffix = m.group(1)
    if suffix == "3":
        return ShareClass.ON
    if suffix in {"4", "5", "6", "7", "8"}:
        return ShareClass.PN
    if suffix == "11":
        return ShareClass.UNIT
    return None


def ticker_class_consistent(ticker: str | None, classe: str | None) -> tuple[bool, ShareClass | None]:
    """Check ticker suffix against a declared class. Returns (ok, expected)."""
    expected = expected_class_for_ticker(ticker)
    if expected is None or not classe:
        return True, expected  # cannot disprove -> not a violation
    declared = classe.strip().upper()
    declared_class = (
        ShareClass.ON if declared.startswith("ON")
        else ShareClass.PN if declared.startswith("PN")
        else ShareClass.UNIT if "UNIT" in declared
        else None
    )
    if declared_class is None:
        return True, expected
    return declared_class == expected, expected
