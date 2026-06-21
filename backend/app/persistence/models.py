"""ORM models: documents (current state) + append-only audit events.

We persist the full ``DocumentResult`` as JSON (the data contract) plus a few
queryable columns, and keep an immutable ``audit_events`` log for the human-in-
the-loop trail — nothing is overwritten, every action is appended.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.persistence.db import Base


class Project(Base):
    """A client project: a batch of uploaded notices analysed together."""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    # DRAFT (uploading) -> ANALYZING -> REVIEW -> COMPLETED
    status: Mapped[str] = mapped_column(String, default="DRAFT", index=True)
    operator: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    documents: Mapped[list[DocumentRow]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class DocumentRow(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str | None] = mapped_column(
        ForeignKey("projects.id"), nullable=True, index=True
    )
    source_file: Mapped[str] = mapped_column(String)
    run_id: Mapped[str] = mapped_column(String, index=True)
    doc_class: Mapped[str] = mapped_column(String)
    event_type: Mapped[str] = mapped_column(String)
    decision: Mapped[str] = mapped_column(String, index=True)
    human_status: Mapped[str | None] = mapped_column(String, nullable=True)
    dq_score: Mapped[float] = mapped_column(Float)
    result: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    events: Mapped[list[AuditEvent]] = relationship(
        back_populates="document", cascade="all, delete-orphan", order_by="AuditEvent.id"
    )
    project: Mapped[Project | None] = relationship(back_populates="documents")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actor: Mapped[str] = mapped_column(String)
    action: Mapped[str] = mapped_column(String)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)

    document: Mapped[DocumentRow] = relationship(back_populates="events")
