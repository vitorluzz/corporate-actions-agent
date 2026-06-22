"""LLM client that prefers the real provider (Gemini) and degrades to the
deterministic stub only when the provider is unavailable — i.e. a depleted free
tier (quota / rate limit) or a credential problem. A persistent outage latches
for the rest of the run so we don't burn time on backoff for every sample.
"""

from __future__ import annotations

import logging

from app.llm.base import ExtractionInput, LLMClient, RawExtraction

logger = logging.getLogger(__name__)

# Substrings (case-insensitive) that identify a *recoverable* provider outage:
# exhausted quota, rate limiting, or bad/absent credentials. Anything else
# (bugs, schema errors, replay-cache misses) is re-raised, never masked.
_RECOVERABLE_SIGNALS = (
    "resource_exhausted",
    "429",
    "quota",
    "rate limit",
    "ratelimit",
    "too many requests",
    "permission_denied",
    "unauthenticated",
    "invalid api key",
    "api key not valid",
    "api_key_invalid",
    "401",
    "403",
)


def _is_recoverable(exc: BaseException) -> bool:
    msg = f"{type(exc).__name__}: {exc}".lower()
    return any(sig in msg for sig in _RECOVERABLE_SIGNALS)


class FallbackLLMClient:
    """Try ``primary`` (Gemini); on a quota/credential outage use ``fallback``
    (the offline stub). ``name``/``model`` reflect whoever served the most
    recent call, so per-document provenance (extraction_method, model) stays
    accurate even when a run degrades mid-batch.
    """

    def __init__(self, *, primary: LLMClient, fallback: LLMClient) -> None:
        self._primary = primary
        self._fallback = fallback
        self._active: LLMClient = primary
        self._degraded = False

    @property
    def name(self) -> str:
        return self._active.name

    @property
    def model(self) -> str:
        return self._active.model

    def extract(
        self, inp: ExtractionInput, *, temperature: float, sample_index: int
    ) -> RawExtraction:
        if not self._degraded:
            try:
                result = self._primary.extract(
                    inp, temperature=temperature, sample_index=sample_index
                )
                self._active = self._primary
                return result
            except Exception as exc:  # noqa: BLE001 — boundary: decide fallback vs re-raise
                if not _is_recoverable(exc):
                    raise
                logger.warning(
                    "LLM provider '%s' unavailable (%s) — degrading to '%s' for "
                    "the rest of this run.",
                    self._primary.name,
                    str(exc).splitlines()[0][:160],
                    self._fallback.name,
                )
                self._degraded = True

        self._active = self._fallback
        return self._fallback.extract(
            inp, temperature=temperature, sample_index=sample_index
        )
