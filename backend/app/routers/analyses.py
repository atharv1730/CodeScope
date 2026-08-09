"""Analysis submission and retrieval endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import (
    Analysis,
    AnalysisStatus,
    CommitActivity,
    Contributor,
    FileConnection,
    FileMetric,
)
from app.reporting import build_complexity_payload, build_structure_payload
from app.reporting_git import build_contributors_payload, build_hotspots_payload
from app.schemas import AnalysisSummary, AnalyzeRequest, AnalyzeResponse, StatusResponse
from app.tasks import run_analysis
from app.utils import InvalidRepoURL, progress_for, validate_github_url

router = APIRouter(tags=["analyses"])

# Statuses that mean "work is done or in flight" — reusable for the cache hit.
_ACTIVE_OR_DONE = (
    AnalysisStatus.queued,
    AnalysisStatus.cloning,
    AnalysisStatus.analyzing_structure,
    AnalysisStatus.analyzing_git,
    AnalysisStatus.analyzing_complexity,
    AnalysisStatus.analyzing_dependencies,
    AnalysisStatus.complete,
)


def _recent_reusable(db: Session, repo_url: str) -> Analysis | None:
    """Return a recent, non-failed analysis for this URL, if within the TTL."""
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=settings.analysis_cache_ttl_seconds)
    stmt = (
        select(Analysis)
        .where(
            Analysis.repo_url == repo_url,
            Analysis.status.in_(_ACTIVE_OR_DONE),
            Analysis.created_at >= cutoff,
        )
        .order_by(Analysis.created_at.desc())
        .limit(1)
    )
    return db.scalars(stmt).first()


@router.post("/analyze", response_model=AnalyzeResponse, status_code=202)
def submit_analysis(payload: AnalyzeRequest, db: Session = Depends(get_db)) -> AnalyzeResponse:
    try:
        clone_url, repo_name = validate_github_url(payload.repo_url)
    except InvalidRepoURL as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Cache: reuse a recent analysis of the same repo instead of re-cloning.
    existing = _recent_reusable(db, clone_url)
    if existing is not None:
        return AnalyzeResponse.model_validate({**existing.__dict__, "cached": True})

    analysis = Analysis(
        id=uuid.uuid4(),
        repo_url=clone_url,
        repo_name=repo_name,
        status=AnalysisStatus.queued,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    run_analysis.delay(str(analysis.id))
    return AnalyzeResponse.model_validate({**analysis.__dict__, "cached": False})


def _get_or_404(db: Session, analysis_id: uuid.UUID) -> Analysis:
    analysis = db.get(Analysis, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis


@router.get("/analyses/{analysis_id}", response_model=AnalysisSummary)
def get_analysis(analysis_id: uuid.UUID, db: Session = Depends(get_db)) -> Analysis:
    return _get_or_404(db, analysis_id)


@router.get("/analyses/{analysis_id}/status", response_model=StatusResponse)
def get_status(analysis_id: uuid.UUID, db: Session = Depends(get_db)) -> StatusResponse:
    analysis = _get_or_404(db, analysis_id)
    return StatusResponse(
        id=analysis.id,
        status=analysis.status,
        error=analysis.error,
        progress=progress_for(analysis.status),
    )


def _file_metrics(db: Session, analysis_id: uuid.UUID) -> list[FileMetric]:
    stmt = select(FileMetric).where(FileMetric.analysis_id == analysis_id)
    return list(db.scalars(stmt).all())


@router.get("/analyses/{analysis_id}/structure")
def get_structure(analysis_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    _get_or_404(db, analysis_id)
    return build_structure_payload(_file_metrics(db, analysis_id))


@router.get("/analyses/{analysis_id}/complexity")
def get_complexity(analysis_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    _get_or_404(db, analysis_id)
    return build_complexity_payload(_file_metrics(db, analysis_id))


@router.get("/analyses/{analysis_id}/contributors")
def get_contributors(analysis_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    _get_or_404(db, analysis_id)
    contributors = db.scalars(
        select(Contributor).where(Contributor.analysis_id == analysis_id)
    ).all()
    activity = db.scalars(
        select(CommitActivity).where(CommitActivity.analysis_id == analysis_id)
    ).all()
    return build_contributors_payload(contributors, activity, _file_metrics(db, analysis_id))


@router.get("/analyses/{analysis_id}/hotspots")
def get_hotspots(analysis_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    _get_or_404(db, analysis_id)
    connections = db.scalars(
        select(FileConnection).where(FileConnection.analysis_id == analysis_id)
    ).all()
    return build_hotspots_payload(_file_metrics(db, analysis_id), connections)
