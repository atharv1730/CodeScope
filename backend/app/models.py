"""SQLAlchemy ORM models mapping the RepoLens PostgreSQL schema.

All five tables are defined up front so the initial migration creates the full
schema. Only `analyses` is exercised on Day 1 (clone + status flow); the rest
are populated by later analysis passes.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AnalysisStatus(str, enum.Enum):
    """Lifecycle of an analysis job. Ordered from submission to completion."""

    queued = "queued"
    cloning = "cloning"
    analyzing_structure = "analyzing_structure"
    analyzing_git = "analyzing_git"
    analyzing_complexity = "analyzing_complexity"
    analyzing_dependencies = "analyzing_dependencies"
    complete = "complete"
    failed = "failed"


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repo_url: Mapped[str] = mapped_column(String(1024), nullable=False, index=True)
    repo_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[AnalysisStatus] = mapped_column(
        SAEnum(AnalysisStatus, name="analysis_status"),
        nullable=False,
        default=AnalysisStatus.queued,
        index=True,
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Summary metrics (filled in as passes complete)
    commit_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    contributor_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_files: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_lines: Mapped[int | None] = mapped_column(Integer, nullable=True)
    primary_language: Mapped[str | None] = mapped_column(String(128), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    file_metrics: Mapped[list["FileMetric"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )
    contributors: Mapped[list["Contributor"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )
    dependencies: Mapped[list["Dependency"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )
    file_connections: Mapped[list["FileConnection"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )


class FileMetric(Base):
    __tablename__ = "file_metrics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_path: Mapped[str] = mapped_column(String(2048), nullable=False)
    language: Mapped[str | None] = mapped_column(String(128), nullable=True)
    lines_of_code: Mapped[int] = mapped_column(Integer, default=0)
    blank_lines: Mapped[int] = mapped_column(Integer, default=0)
    comment_lines: Mapped[int] = mapped_column(Integer, default=0)
    complexity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    function_count: Mapped[int] = mapped_column(Integer, default=0)
    change_frequency: Mapped[int] = mapped_column(Integer, default=0)
    last_changed: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    top_contributor: Mapped[str | None] = mapped_column(String(512), nullable=True)

    analysis: Mapped["Analysis"] = relationship(back_populates="file_metrics")


class Contributor(Base):
    __tablename__ = "contributors"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    email: Mapped[str | None] = mapped_column(String(512), nullable=True)
    commit_count: Mapped[int] = mapped_column(Integer, default=0)
    first_commit: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_commit: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    files_touched: Mapped[int] = mapped_column(Integer, default=0)

    analysis: Mapped["Analysis"] = relationship(back_populates="contributors")


class Dependency(Base):
    __tablename__ = "dependencies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    current_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    latest_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_outdated: Mapped[bool] = mapped_column(Boolean, default=False)
    versions_behind: Mapped[int] = mapped_column(Integer, default=0)
    has_vulnerability: Mapped[bool] = mapped_column(Boolean, default=False)
    vulnerability_details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    analysis: Mapped["Analysis"] = relationship(back_populates="dependencies")


class FileConnection(Base):
    __tablename__ = "file_connections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_file: Mapped[str] = mapped_column(String(2048), nullable=False)
    target_file: Mapped[str] = mapped_column(String(2048), nullable=False)
    # "import" or "co_change"
    connection_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    analysis: Mapped["Analysis"] = relationship(back_populates="file_connections")
