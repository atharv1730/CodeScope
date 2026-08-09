"""Pydantic request/response models for the API layer."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.models import AnalysisStatus

_ORM = ConfigDict(from_attributes=True)


class AnalyzeRequest(BaseModel):
    repo_url: str

    @field_validator("repo_url")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


class AnalyzeResponse(BaseModel):
    model_config = _ORM

    id: uuid.UUID
    repo_url: str
    repo_name: str | None
    status: AnalysisStatus
    created_at: datetime
    cached: bool = False


class StatusResponse(BaseModel):
    """Lightweight payload for polling."""

    model_config = _ORM

    id: uuid.UUID
    status: AnalysisStatus
    error: str | None = None
    progress: int = 0  # 0-100, derived from status


class AnalysisSummary(BaseModel):
    model_config = _ORM

    id: uuid.UUID
    repo_url: str
    repo_name: str | None
    status: AnalysisStatus
    error: str | None
    commit_count: int | None
    contributor_count: int | None
    total_files: int | None
    total_lines: int | None
    primary_language: str | None
    created_at: datetime
    completed_at: datetime | None


class HealthResponse(BaseModel):
    status: str
    database: str
    redis: str
    queued_jobs: int | None = None
    workers_online: int | None = None
