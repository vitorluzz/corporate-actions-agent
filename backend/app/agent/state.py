"""LangGraph pipeline state (data only; deps are injected into nodes)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.agent.assembly import FieldSignals
from app.agent.selfconsistency import Consensus
from app.domain.schemas import (
    DataQualityScore,
    DocumentResult,
    ExtractedField,
    GoldenMatch,
    GuardrailResult,
    Record,
    Routing,
    ToolCall,
)
from app.extraction.pdf import LoadedDocument
from app.llm.base import RawExtraction


class PipelineState(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    doc: LoadedDocument
    run_id: str

    samples: list[RawExtraction] = Field(default_factory=list)
    consensus: Consensus | None = None
    record: Record | None = None
    fields: list[ExtractedField] = Field(default_factory=list)
    signals: list[FieldSignals] = Field(default_factory=list)
    guardrails: list[GuardrailResult] = Field(default_factory=list)
    golden_match: GoldenMatch | None = None
    dq: DataQualityScore | None = None
    routing: Routing | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)

    result: DocumentResult | None = None
