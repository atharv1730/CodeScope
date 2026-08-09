"""Structure pass: walk the file tree, record per-file metrics, summarize.

Creates one `file_metrics` row per recognized code/text file and fills the
summary fields on the `analyses` row (total_files, total_lines,
primary_language). Complexity and git fields are populated by later passes.
"""
from __future__ import annotations

import os
from collections import defaultdict

from sqlalchemy.orm import Session

from app.analysis.filereader import count_file
from app.analysis.languages import IGNORED_DIRS
from app.models import Analysis, FileMetric


def _walk_code_files(root: str):
    """Yield (abs_path, rel_path) for candidate files, skipping ignored dirs."""
    for dirpath, dirnames, filenames in os.walk(root):
        # Prune ignored directories in place so os.walk doesn't descend.
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
        for name in filenames:
            abs_path = os.path.join(dirpath, name)
            if os.path.islink(abs_path):
                continue
            rel_path = os.path.relpath(abs_path, root)
            yield abs_path, rel_path


def analyze_structure(db: Session, analysis: Analysis, clone_path: str) -> int:
    """Populate file_metrics + analysis summary. Returns number of files recorded."""
    lang_lines: dict[str, int] = defaultdict(int)
    total_code = 0
    total_physical = 0
    metrics: list[FileMetric] = []

    for abs_path, rel_path in _walk_code_files(clone_path):
        result = count_file(abs_path, rel_path)
        if result is None:
            continue
        c = result.counts
        metrics.append(
            FileMetric(
                analysis_id=analysis.id,
                file_path=rel_path,
                language=result.language,
                lines_of_code=c.code,
                blank_lines=c.blank,
                comment_lines=c.comment,
            )
        )
        lang_lines[result.language] += c.code
        total_code += c.code
        total_physical += c.total

    if metrics:
        db.bulk_save_objects(metrics)

    analysis.total_files = len(metrics)
    analysis.total_lines = total_physical
    analysis.primary_language = (
        max(lang_lines.items(), key=lambda kv: kv[1])[0] if lang_lines else None
    )
    db.commit()
    return len(metrics)
