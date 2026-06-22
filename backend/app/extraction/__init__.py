"""Document extraction: PDF parsing, native/scan detection, provenance."""

from app.extraction.pdf import LoadedDocument, Page, Word, load_document
from app.extraction.provenance import Location, build_evidence, locate_in_document

__all__ = [
    "LoadedDocument",
    "Page",
    "Word",
    "load_document",
    "Location",
    "build_evidence",
    "locate_in_document",
]
