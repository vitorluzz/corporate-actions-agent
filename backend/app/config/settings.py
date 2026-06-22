"""Application settings + the **documented assumptions** the case asks for.

Thresholds that define "baixa confiança" and coherence tolerances live here so
they are explicit, versioned and auditable (not buried in code). Override via
environment variables or a ``.env`` file.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# repo root = .../case-assetservicing ; this file = backend/app/config/settings.py
REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(REPO_ROOT / ".env"), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # -- LLM ----------------------------------------------------------------
    google_api_key: str | None = Field(default=None)
    # "gemini" uses the real API; "stub" runs fully offline (deterministic).
    llm_provider: str = Field(default="auto")  # auto | gemini | stub
    gemini_model: str = Field(default="gemini-2.5-flash")
    gemini_model_fallback: str = Field(default="gemini-2.5-flash-lite")

    # -- Self-consistency sampling (probabilistic event-type classification) -
    self_consistency_n: int = Field(default=5, ge=1, le=15)
    self_consistency_temperature: float = Field(default=0.5, ge=0.0, le=2.0)
    extraction_temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    llm_max_retries: int = Field(default=5, ge=0)

    # -- Routing thresholds (DOCUMENTED ASSUMPTIONS) ------------------------
    # A field is "low confidence" when p_correct falls below this.
    field_review_threshold: float = Field(default=0.70, ge=0.0, le=1.0)
    # Event-type is uncertain when normalized entropy exceeds this.
    type_entropy_review_threshold: float = Field(default=0.35, ge=0.0, le=1.0)
    # Document DQ score below this routes to human review.
    dq_review_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    # Minimum value↔source fuzzy score to consider a value "grounded".
    groundedness_min_score: float = Field(default=0.60, ge=0.0, le=1.0)
    # Scan extractions get a flat confidence penalty (OCR uncertainty).
    scan_confidence_penalty: float = Field(default=0.15, ge=0.0, le=1.0)

    # -- Coherence-rule parameters ------------------------------------------
    jcp_irrf_rate: float = Field(default=0.15, ge=0.0, le=1.0)
    jcp_net_tolerance: float = Field(default=0.02, ge=0.0, le=1.0)  # ±2%

    # -- Paths --------------------------------------------------------------
    documents_dir: Path = Field(default=REPO_ROOT / "documents")
    uploads_dir: Path = Field(default=REPO_ROOT / "uploads")
    golden_records_csv: Path = Field(default=REPO_ROOT / "golden_records" / "golden records.csv")
    outputs_dir: Path = Field(default=REPO_ROOT / "outputs")
    cache_dir: Path = Field(default=REPO_ROOT / ".cache" / "llm")

    # -- Persistence --------------------------------------------------------
    database_url: str = Field(
        default="postgresql+psycopg://asset:asset@localhost:5432/asset_servicing"
    )

    # -- Behaviour ----------------------------------------------------------
    use_llm_cache: bool = Field(default=True)
    replay_only: bool = Field(default=False)  # --replay: never call the LLM

    @property
    def effective_provider(self) -> str:
        if self.llm_provider != "auto":
            return self.llm_provider
        return "gemini" if self.google_api_key else "stub"


@lru_cache
def get_settings() -> Settings:
    return Settings()
