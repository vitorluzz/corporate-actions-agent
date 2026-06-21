"""PDF ingestion: native-vs-scanned detection, text+word boxes, page rendering.

Native PDFs give us a text layer + per-word bounding boxes (provenance anchors).
Scanned PDFs have (almost) no text layer, so we render pages to PNG for the
vision model. Detection is a simple, defensible heuristic: characters of
extracted text per page.
"""

from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF

from app.domain.enums import DocumentClass

# Below this many chars of extracted text, we treat a document as scanned.
_SCANNED_TEXT_CHAR_THRESHOLD = 80
_RENDER_DPI = 200


@dataclass(frozen=True)
class Word:
    x0: float
    y0: float
    x1: float
    y1: float
    text: str
    page: int


@dataclass
class Page:
    number: int               # 1-based
    text: str
    words: list[Word] = field(default_factory=list)
    image_b64: str | None = None  # populated for scanned docs


@dataclass
class LoadedDocument:
    doc_id: str
    source_file: str
    doc_hash: str
    doc_class: DocumentClass
    pages: list[Page]

    @property
    def full_text(self) -> str:
        return "\n".join(p.text for p in self.pages)

    @property
    def page_count(self) -> int:
        return len(self.pages)

    @property
    def images_b64(self) -> list[str]:
        return [p.image_b64 for p in self.pages if p.image_b64]

    def page(self, number: int) -> Page | None:
        return next((p for p in self.pages if p.number == number), None)


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()[:16]


def _render_png_b64(page: fitz.Page, dpi: int = _RENDER_DPI) -> str:
    pix = page.get_pixmap(dpi=dpi)
    return base64.b64encode(pix.tobytes("png")).decode("ascii")


def render_page_png(path: str | Path, page_number: int = 1, dpi: int = 150) -> bytes:
    """Render a single PDF page to PNG bytes (works for native and scanned docs).

    Used by the console to display the document as an image — robust in any
    browser (no PDF plugin needed) and the basis for bbox-overlay highlighting.
    """
    with fitz.open(path) as pdf:
        page = pdf[max(0, min(page_number - 1, pdf.page_count - 1))]
        return page.get_pixmap(dpi=dpi).tobytes("png")


def load_document(path: str | Path) -> LoadedDocument:
    path = Path(path)
    doc_hash = _hash_file(path)
    pages: list[Page] = []

    with fitz.open(path) as pdf:
        total_chars = 0
        raw_pages: list[tuple[int, str, list[Word], fitz.Page]] = []
        for i, page in enumerate(pdf, start=1):
            text = page.get_text("text") or ""
            total_chars += len(text.strip())
            words = [
                Word(x0=w[0], y0=w[1], x1=w[2], y1=w[3], text=w[4], page=i)
                for w in page.get_text("words")
            ]
            raw_pages.append((i, text, words, page))

        is_scanned = total_chars < _SCANNED_TEXT_CHAR_THRESHOLD
        doc_class = DocumentClass.SCANNED if is_scanned else DocumentClass.NATIVE

        for i, text, words, page in raw_pages:
            image_b64 = _render_png_b64(page) if is_scanned else None
            pages.append(Page(number=i, text=text, words=words, image_b64=image_b64))

    return LoadedDocument(
        doc_id=path.stem,
        source_file=path.name,
        doc_hash=doc_hash,
        doc_class=doc_class,
        pages=pages,
    )
