"""Complexity pass: cyclomatic complexity + function count for Python files.

radon computes cyclomatic complexity per code block (function/method/class).
We store the file's total complexity as `complexity_score` and the number of
callable blocks as `function_count`. Non-Python files keep complexity_score
NULL (radon is Python-only) but still carry their line counts from the
structure pass.
"""
from __future__ import annotations

import os

from radon.complexity import cc_visit
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Analysis, FileMetric


def _analyze_python_file(abs_path: str) -> tuple[float, int] | None:
    """Return (total_complexity, function_count) or None if unparseable."""
    try:
        with open(abs_path, "r", encoding="utf-8", errors="replace") as fh:
            source = fh.read()
    except OSError:
        return None
    try:
        blocks = cc_visit(source)
    except (SyntaxError, ValueError):
        return None
    if not blocks:
        return 0.0, 0
    total = float(sum(b.complexity for b in blocks))
    return total, len(blocks)


def analyze_complexity(db: Session, analysis: Analysis, clone_path: str) -> int:
    """Update Python file_metrics rows with complexity. Returns files scored."""
    stmt = select(FileMetric).where(
        FileMetric.analysis_id == analysis.id,
        FileMetric.language == "Python",
    )
    rows = db.scalars(stmt).all()

    scored = 0
    for row in rows:
        abs_path = os.path.join(clone_path, row.file_path)
        result = _analyze_python_file(abs_path)
        if result is None:
            continue
        row.complexity_score, row.function_count = result
        scored += 1

    db.commit()
    return scored
