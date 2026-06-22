"""LLM boundary types.

The agent depends only on this abstraction, never on a concrete provider. That
keeps the core provider-agnostic (Gemini today, anything tomorrow) and lets the
whole pipeline run offline via the deterministic stub for tests and reproducible
outputs.

One ``extract`` call returns BOTH the candidate event type and the per-field
values+evidence. Self-consistency = sampling this call N times, which yields the
event-type vote distribution *and* per-field agreement from the same samples.
"""

from __future__ import annotations

import hashlib
import json
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

from app.domain.enums import EventType


class ExtractionInput(BaseModel):
    """Everything the model needs to extract one document."""

    doc_id: str
    doc_hash: str
    text: str | None = None              # native text layer (if any)
    image_b64: list[str] = Field(default_factory=list)  # rendered pages for vision
    is_scan: bool = False


class RawField(BaseModel):
    """Model's raw view of one field, before deterministic fusion."""

    name: str
    value: str | None = None
    quote: str | None = None             # verbatim snippet supporting the value
    page: int | None = None
    confidence: float = 0.5              # self-reported [0,1]
    rationale: str = ""


class RawExtraction(BaseModel):
    """Single-sample model output (event type + fields)."""

    event_type: EventType = EventType.INCERTO
    event_type_rationale: str = ""
    fields: list[RawField] = Field(default_factory=list)

    def field(self, name: str) -> RawField | None:
        return next((f for f in self.fields if f.name == name), None)


def prompt_hash(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()[:16]


def stable_key(payload: dict) -> str:
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:24]


@runtime_checkable
class LLMClient(Protocol):
    """Provider-agnostic extraction client."""

    name: str
    model: str

    def extract(
        self, inp: ExtractionInput, *, temperature: float, sample_index: int
    ) -> RawExtraction:
        """Return one extraction sample for the document."""
        ...
