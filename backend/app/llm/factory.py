"""LLM client factory — picks provider from settings and wraps with the cache."""

from __future__ import annotations

from app.config.settings import Settings, get_settings
from app.llm.base import LLMClient
from app.llm.cache import CachedLLMClient


def build_llm_client(settings: Settings | None = None) -> LLMClient:
    settings = settings or get_settings()
    provider = settings.effective_provider

    inner: LLMClient
    if provider == "gemini":
        from app.llm.gemini import GeminiClient

        if not settings.google_api_key:
            raise RuntimeError("llm_provider=gemini but GOOGLE_API_KEY is not set.")
        inner = GeminiClient(
            model=settings.gemini_model,
            api_key=settings.google_api_key,
            max_retries=settings.llm_max_retries,
            fallback_model=settings.gemini_model_fallback,
        )
    else:
        from app.llm.stub import StubClient

        inner = StubClient()

    return CachedLLMClient(
        inner,
        cache_dir=settings.cache_dir,
        enabled=settings.use_llm_cache,
        replay_only=settings.replay_only,
    )
