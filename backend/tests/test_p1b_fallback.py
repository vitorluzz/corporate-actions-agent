"""P1b tests: provider fallback (Gemini → stub) on quota/credential outage."""

from __future__ import annotations

import pytest

from app.llm.base import ExtractionInput, RawExtraction, RawField
from app.llm.fallback import FallbackLLMClient, _is_recoverable


class _FakeClient:
    def __init__(self, name: str, model: str, *, raises: Exception | None = None) -> None:
        self.name = name
        self.model = model
        self._raises = raises
        self.calls = 0

    def extract(self, inp: ExtractionInput, *, temperature: float, sample_index: int) -> RawExtraction:
        self.calls += 1
        if self._raises is not None:
            raise self._raises
        return RawExtraction(fields=[RawField(name="tag", value=self.name)])


_INP = ExtractionInput(doc_id="x", doc_hash="h", text="t")


def test_recoverable_signal_detection() -> None:
    assert _is_recoverable(RuntimeError("429 RESOURCE_EXHAUSTED: quota exceeded"))
    assert _is_recoverable(Exception("PERMISSION_DENIED: API key not valid"))
    assert not _is_recoverable(ValueError("schema validation failed"))
    assert not _is_recoverable(RuntimeError("replay_only=True but no cached sample"))


def test_prefers_primary_when_healthy() -> None:
    primary = _FakeClient("cached:gemini", "gemini-2.5-flash")
    fallback = _FakeClient("stub", "heuristic")
    client = FallbackLLMClient(primary=primary, fallback=fallback)

    out = client.extract(_INP, temperature=0.0, sample_index=0)
    assert out.fields[0].value == "cached:gemini"
    assert client.name == "cached:gemini" and client.model == "gemini-2.5-flash"
    assert fallback.calls == 0


def test_degrades_to_stub_on_quota_and_latches() -> None:
    primary = _FakeClient(
        "cached:gemini", "gemini-2.5-flash",
        raises=RuntimeError("429 RESOURCE_EXHAUSTED: quota exhausted"),
    )
    fallback = _FakeClient("stub", "heuristic")
    client = FallbackLLMClient(primary=primary, fallback=fallback)

    # first call degrades; provenance now reflects the stub
    out = client.extract(_INP, temperature=0.0, sample_index=0)
    assert out.fields[0].value == "stub"
    assert client.name == "stub" and client.model == "heuristic"

    # latched: subsequent calls go straight to stub, primary not retried
    client.extract(_INP, temperature=0.0, sample_index=1)
    assert primary.calls == 1
    assert fallback.calls == 2


def test_non_recoverable_error_is_reraised() -> None:
    primary = _FakeClient(
        "cached:gemini", "gemini-2.5-flash", raises=ValueError("schema mismatch")
    )
    fallback = _FakeClient("stub", "heuristic")
    client = FallbackLLMClient(primary=primary, fallback=fallback)

    with pytest.raises(ValueError):
        client.extract(_INP, temperature=0.0, sample_index=0)
    assert fallback.calls == 0
