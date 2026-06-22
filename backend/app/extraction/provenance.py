"""Provenance: map an extracted value/quote back to its position in the PDF.

Returns a char span + union bounding box + a fuzzy match score. The match score
doubles as the **groundedness** signal: a value we cannot anchor in the source
is flagged (anti-hallucination).
"""

from __future__ import annotations

from dataclasses import dataclass

from rapidfuzz import fuzz

from app.domain.enums import EvidenceSource
from app.domain.schemas import BBox, Evidence
from app.extraction.pdf import LoadedDocument, Page, Word

_MIN_FUZZY_SCORE = 60.0


@dataclass(frozen=True)
class Location:
    page: int
    char_span: tuple[int, int]
    bbox: BBox
    score: float  # 0..1


def _page_index(words: list[Word]) -> tuple[str, list[tuple[int, int, int]]]:
    """Reconstruct page text and record each word's [start,end) char range."""
    parts: list[str] = []
    spans: list[tuple[int, int, int]] = []
    pos = 0
    for i, w in enumerate(words):
        if i > 0:
            parts.append(" ")
            pos += 1
        start = pos
        parts.append(w.text)
        pos += len(w.text)
        spans.append((start, pos, i))
    return "".join(parts), spans


def _union_bbox(words: list[Word], idxs: list[int], coord_system: str = "pdf_points") -> BBox:
    return BBox(
        x0=min(words[i].x0 for i in idxs),
        y0=min(words[i].y0 for i in idxs),
        x1=max(words[i].x1 for i in idxs),
        y1=max(words[i].y1 for i in idxs),
        coord_system=coord_system,
    )


def locate_in_page(value: str | None, page: Page) -> Location | None:
    if not value or not value.strip() or not page.words:
        return None

    text, spans = _page_index(page.words)
    low = text.lower()
    needle = value.strip().lower()

    idx = low.find(needle)
    if idx >= 0:
        span = (idx, idx + len(needle))
        score = 1.0
    else:
        align = fuzz.partial_ratio_alignment(needle, low)
        if align is None or align.score < _MIN_FUZZY_SCORE:
            return None
        span = (align.dest_start, align.dest_end)
        score = align.score / 100.0

    word_idxs = [wi for (s, e, wi) in spans if s < span[1] and e > span[0]]
    if not word_idxs:
        return None

    return Location(
        page=page.number,
        char_span=span,
        bbox=_union_bbox(page.words, word_idxs, "image_px@200dpi" if page.ocr else "pdf_points"),
        score=score,
    )


def locate_in_document(value: str | None, doc: LoadedDocument) -> Location | None:
    """Return the best location for ``value`` across all pages."""
    best: Location | None = None
    for page in doc.pages:
        loc = locate_in_page(value, page)
        if loc and (best is None or loc.score > best.score):
            best = loc
    return best


def build_evidence(
    value: str | None,
    quote: str | None,
    doc: LoadedDocument,
) -> tuple[Evidence | None, float]:
    """Anchor a value in the native text layer. Returns (evidence, score)."""
    # Prefer locating the value itself; fall back to the model-provided quote.
    loc = locate_in_document(value, doc) or locate_in_document(quote, doc)
    if loc is None:
        return None, 0.0
    page = doc.page(loc.page)
    snippet = quote
    if page and not snippet:
        s, e = loc.char_span
        snippet = page.text[max(0, s - 20) : e + 20].strip()
    evidence = Evidence(
        source=EvidenceSource.OCR if (page and page.ocr) else EvidenceSource.NATIVE_TEXT,
        quote=snippet,
        page=loc.page,
        bbox=loc.bbox,
        char_span=loc.char_span,
        match_score=round(loc.score, 4),
    )
    return evidence, loc.score
