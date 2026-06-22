"""LLM client factory — picks provider from settings and wraps with the cache."""

from __future__ import annotations

from app.config.settings import Settings, get_settings
from app.llm.base import LLMClient
from app.llm.cache import CachedLLMClient


def build_llm_client(settings: Settings | None = None) -> LLMClient:
    settings = settings or get_settings()
    provider = settings.effective_provider

    if provider == "gemini":
        from app.llm.fallback import FallbackLLMClient
        from app.llm.gemini import GeminiClient
        from app.llm.stub import StubClient

        if not settings.google_api_key:
            raise RuntimeError("llm_provider=gemini but GOOGLE_API_KEY is not set.")
        gemini = GeminiClient(
            model=settings.gemini_model,
            api_key=settings.google_api_key,
            max_retries=settings.llm_max_retries,
            fallback_model=settings.gemini_model_fallback,
        )
        # Cache the real provider's responses (idempotent re-runs, --replay, quota savings).
        cached_gemini = CachedLLMClient(
            gemini,
            cache_dir=settings.cache_dir,
            enabled=settings.use_llm_cache,
            replay_only=settings.replay_only,
        )
        # Always prefer Gemini; degrade to the deterministic stub only when the
        # free tier is depleted (quota / rate limit) or credentials fail.
        return FallbackLLMClient(primary=cached_gemini, fallback=StubClient())

    # provider == "stub": no API key (auto) or explicitly requested → fully offline.
    from app.llm.stub import StubClient

    return CachedLLMClient(
        StubClient(),
        cache_dir=settings.cache_dir,
        enabled=settings.use_llm_cache,
        replay_only=settings.replay_only,
    )
