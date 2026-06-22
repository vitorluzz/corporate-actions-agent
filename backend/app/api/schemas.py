"""API request/response models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DocumentListItem(BaseModel):
    id: str
    source_file: str
    doc_class: str
    event_type: str
    decision: str
    human_status: str | None = None
    dq_score: float


class ReviewRequest(BaseModel):
    actor: str = "operator"
    decision: str = Field(default="save", description="approve | reject | save")
    field_corrections: dict[str, str] = Field(default_factory=dict)
    note: str = ""


class AuditEventOut(BaseModel):
    id: int
    ts: str
    actor: str
    action: str
    detail: dict


class CreateProjectRequest(BaseModel):
    name: str
    operator: str | None = None


class RenameProjectRequest(BaseModel):
    name: str


class ProjectOut(BaseModel):
    id: str
    name: str
    status: str
    operator: str | None = None
    created_at: str = ""
    total: int = 0
    decided: int = 0
    pending: int = 0
