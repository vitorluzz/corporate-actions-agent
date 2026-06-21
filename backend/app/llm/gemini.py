"""Gemini implementation of the LLM boundary (free-tier friendly).

Uses ``langchain-google-genai`` with structured output (``with_structured_output``)
for schema-enforced extraction, native multimodal vision for scans, and
exponential backoff on rate-limit / quota errors.
"""

from __future__ import annotations

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from app.llm.base import ExtractionInput, RawExtraction
from app.llm.prompts import SYSTEM_PROMPT, build_text_prompt, build_vision_prompt


class GeminiClient:
    """Concrete :class:`~app.llm.base.LLMClient` backed by Gemini."""

    def __init__(
        self,
        *,
        model: str,
        api_key: str,
        max_retries: int = 5,
        fallback_model: str | None = None,
    ) -> None:
        self.name = "gemini"
        self.model = model
        self._api_key = api_key
        self._fallback_model = fallback_model
        self._max_retries = max_retries
        self._structured = self._build(model)
        self._structured_fallback = (
            self._build(fallback_model) if fallback_model else None
        )

    def _build(self, model: str):
        from langchain_google_genai import ChatGoogleGenerativeAI

        llm = ChatGoogleGenerativeAI(
            model=model,
            api_key=self._api_key,
            temperature=0.0,
            max_retries=0,  # we own retry/backoff via tenacity
        )
        return llm.with_structured_output(RawExtraction)

    def _messages(self, inp: ExtractionInput):
        from langchain_core.messages import HumanMessage, SystemMessage

        if inp.is_scan and inp.image_b64:
            parts: list[dict] = [{"type": "text", "text": build_vision_prompt(inp.doc_id)}]
            for b64 in inp.image_b64:
                parts.append(
                    {
                        "type": "image_url",
                        "image_url": f"data:image/png;base64,{b64}",
                    }
                )
            return [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=parts)]

        prompt = build_text_prompt(inp.doc_id, inp.text or "")
        return [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=prompt)]

    def extract(
        self, inp: ExtractionInput, *, temperature: float, sample_index: int
    ) -> RawExtraction:
        messages = self._messages(inp)

        @retry(
            reraise=True,
            stop=stop_after_attempt(self._max_retries + 1),
            wait=wait_exponential_jitter(initial=2, max=60),
            retry=retry_if_exception_type(Exception),
        )
        def _call(structured) -> RawExtraction:
            return structured.invoke(
                messages, config={"configurable": {"temperature": temperature}}
            )

        try:
            return _call(self._structured)
        except Exception:
            if self._structured_fallback is not None:
                return _call(self._structured_fallback)
            raise
