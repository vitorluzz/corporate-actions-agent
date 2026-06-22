"""OCR for scanned PDFs (Tesseract via pytesseract).

Kept behind a graceful guard: if the ``tesseract`` binary or ``pytesseract`` are
not installed, OCR silently yields nothing and the pipeline degrades to the
previous behaviour (scan → human review) instead of crashing. Tesseract gives us
both a text layer (so the offline extractor has something to parse) and
word-level boxes (provenance anchors, in rendered-image pixel coordinates).
"""

from __future__ import annotations

import io

import fitz  # PyMuPDF

# Brazilian corporate-event notices are Portuguese; keep English for codes/labels.
_OCR_LANG = "por+eng"

# (x0, y0, x1, y1, text) in rendered-image pixel coordinates.
OcrBox = tuple[float, float, float, float, str]


def ocr_available() -> bool:
    try:
        import pytesseract

        pytesseract.get_tesseract_version()
        return True
    except Exception:  # noqa: BLE001 - any failure means "no OCR available"
        return False


def ocr_page(page: fitz.Page, dpi: int = 200) -> tuple[str, list[OcrBox]]:
    """OCR one rendered page → (text, word boxes). Returns ("", []) on any failure."""
    try:
        import pytesseract
        from PIL import Image
    except Exception:  # noqa: BLE001 - pytesseract/Pillow missing
        return "", []
    try:
        png = page.get_pixmap(dpi=dpi).tobytes("png")
        img = Image.open(io.BytesIO(png))
        text = pytesseract.image_to_string(img, lang=_OCR_LANG)
        data = pytesseract.image_to_data(img, lang=_OCR_LANG, output_type=pytesseract.Output.DICT)
        boxes: list[OcrBox] = []
        for word, left, top, w, h, conf in zip(
            data["text"], data["left"], data["top"], data["width"], data["height"], data["conf"],
            strict=False,
        ):
            if not str(word).strip():
                continue
            try:
                if float(conf) < 0:  # -1 marks non-text layout boxes
                    continue
            except (TypeError, ValueError):
                pass
            boxes.append((float(left), float(top), float(left + w), float(top + h), str(word)))
        return text, boxes
    except Exception:  # noqa: BLE001 - OCR is best-effort, never fatal
        return "", []
