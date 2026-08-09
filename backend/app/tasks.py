"""Celery tasks orchestrating the analysis pipeline.

Day 1 scope: clone the repo and drive the status state machine. Later passes
(structure, git, complexity, dependencies) plug into `run_analysis` between the
`cloning` and `complete` states.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.analysis.clone import CloneError, cleanup_clone, clone_repo
from app.analysis.complexity import analyze_complexity
from app.analysis.git import analyze_git
from app.analysis.structure import analyze_structure
from app.celery_app import celery_app
from app.database import SessionLocal
from app.models import Analysis, AnalysisStatus

logger = logging.getLogger(__name__)


def _set_status(analysis_id: str, status: AnalysisStatus, *, error: str | None = None) -> None:
    with SessionLocal() as db:
        analysis = db.get(Analysis, analysis_id)
        if analysis is None:
            logger.warning("Analysis %s vanished before status update", analysis_id)
            return
        analysis.status = status
        if error is not None:
            analysis.error = error
        if status in (AnalysisStatus.complete, AnalysisStatus.failed):
            analysis.completed_at = datetime.now(timezone.utc)
        db.commit()


@celery_app.task(name="app.tasks.run_analysis", bind=True)
def run_analysis(self, analysis_id: str) -> str:
    """Entry point: clone the repo, then run analysis passes.

    Returns the analysis_id (Celery result backend holds only this pointer;
    all real data is written to Postgres by the passes themselves).
    """
    with SessionLocal() as db:
        analysis = db.get(Analysis, analysis_id)
        if analysis is None:
            logger.error("run_analysis called with unknown id %s", analysis_id)
            return analysis_id
        clone_url = analysis.repo_url

    clone_path: str | None = None
    try:
        _set_status(analysis_id, AnalysisStatus.cloning)
        clone_path = clone_repo(clone_url, analysis_id)

        # --- Structure pass (Day 2) ---
        _set_status(analysis_id, AnalysisStatus.analyzing_structure)
        with SessionLocal() as db:
            analysis = db.get(Analysis, analysis_id)
            file_count = analyze_structure(db, analysis, clone_path)
        logger.info("Analysis %s: recorded %d files", analysis_id, file_count)

        # --- Git history pass (Day 3) ---
        _set_status(analysis_id, AnalysisStatus.analyzing_git)
        with SessionLocal() as db:
            analysis = db.get(Analysis, analysis_id)
            git_stats = analyze_git(db, analysis, clone_path)
        logger.info("Analysis %s: git %s", analysis_id, git_stats)

        # --- Complexity pass (Day 2) ---
        _set_status(analysis_id, AnalysisStatus.analyzing_complexity)
        with SessionLocal() as db:
            analysis = db.get(Analysis, analysis_id)
            scored = analyze_complexity(db, analysis, clone_path)
        logger.info("Analysis %s: scored %d Python files", analysis_id, scored)

        # --- Dependencies pass (Day 4) plugs in here ---

        _set_status(analysis_id, AnalysisStatus.complete)
        logger.info("Analysis %s complete", analysis_id)
    except CloneError as exc:
        logger.warning("Clone failed for %s: %s", analysis_id, exc)
        _set_status(analysis_id, AnalysisStatus.failed, error=str(exc))
    except Exception as exc:  # noqa: BLE001 - surface any failure to the user
        logger.exception("Unexpected failure analyzing %s", analysis_id)
        _set_status(analysis_id, AnalysisStatus.failed, error=f"Internal error: {exc}")
    finally:
        if clone_path:
            cleanup_clone(clone_path)

    return analysis_id
