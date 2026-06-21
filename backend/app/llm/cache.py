"""On-disk response cache → idempotent re-runs, free-tier quota savings, and
**offline reproduction** of committed outputs (``--replay``).

Keyed by (doc_hash, prompt_hash, sample_index, temperature, model). Cached
samples can be committed to the repo so a grader reproduces the exact batch
output without spending any API quota.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.llm.base import (
    ExtractionInput,
    LLMClient,
    RawExtraction,
    prompt_hash,
    stable_key,
)


class CachedLLMClient:
    """Decorator that memoizes extraction samples to ``cache_dir``."""

    def __init__(
        self,
        inner: LLMClient,
        cache_dir: str | Path,
        *,
        enabled: bool = True,
        replay_only: bool = False,
    ) -> None:
        self._inner = inner
        self._dir = Path(cache_dir)
        self._enabled = enabled
        self._replay_only = replay_only
        self.name = f"cached:{inner.name}"
        self.model = inner.model
        if enabled:
            self._dir.mkdir(parents=True, exist_ok=True)

    def _key_path(self, inp: ExtractionInput, temperature: float, sample_index: int) -> Path:
        key = stable_key(
            {
                "doc_hash": inp.doc_hash,
                "model": self._inner.model,
                "phash": prompt_hash(inp.text or "", "vision" if inp.is_scan else "text"),
                "temperature": round(temperature, 3),
                "sample": sample_index,
            }
        )
        return self._dir / f"{inp.doc_id}.{sample_index}.{key}.json"

    def extract(
        self, inp: ExtractionInput, *, temperature: float, sample_index: int
    ) -> RawExtraction:
        path = self._key_path(inp, temperature, sample_index)
        if self._enabled and path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return RawExtraction.model_validate(data)

        if self._replay_only:
            raise RuntimeError(
                f"replay_only=True but no cached sample for {inp.doc_id} "
                f"(sample {sample_index}). Run once online to populate the cache."
            )

        result = self._inner.extract(
            inp, temperature=temperature, sample_index=sample_index
        )
        if self._enabled:
            path.write_text(
                json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        return result
