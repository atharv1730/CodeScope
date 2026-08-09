"""Python import graph: map which repo files import which other repo files.

Only intra-repo imports are edges (external packages are covered by the
dependency pass). Resolution is a pragmatic best-effort over a module index
built from the repo's Python files — it handles absolute and relative imports
but does not execute code, so dynamic imports are out of scope.
"""
from __future__ import annotations

import ast
import os

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Analysis, FileConnection, FileMetric

MAX_IMPORT_EDGES = 2000


def _module_name(rel_path: str) -> tuple[str, bool]:
    """Return (dotted_module, is_package) for a repo-relative .py path."""
    no_ext = rel_path[:-3] if rel_path.endswith(".py") else rel_path
    parts = no_ext.split("/")
    if parts[-1] == "__init__":
        parts = parts[:-1]
        return ".".join(parts), True
    return ".".join(parts), False


def build_module_index(py_files: list[str]) -> dict[str, str]:
    """Map dotted module (and package) names to their file path."""
    index: dict[str, str] = {}
    for rel in py_files:
        mod, _is_pkg = _module_name(rel)
        if mod:
            index[mod] = rel
    return index


def _package_parts(rel_path: str) -> list[str]:
    """Directory parts that form the package a module lives in."""
    return os.path.dirname(rel_path).split("/") if os.path.dirname(rel_path) else []


def extract_imports(source: str) -> list[tuple[int, str | None, tuple[str, ...]]]:
    """Return (level, module, names) tuples from a Python source string."""
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return []
    out: list[tuple[int, str | None, tuple[str, ...]]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                out.append((0, alias.name, ()))
        elif isinstance(node, ast.ImportFrom):
            names = tuple(a.name for a in node.names)
            out.append((node.level or 0, node.module, names))
    return out


def _candidates(
    rel_path: str, level: int, module: str | None, names: tuple[str, ...]
) -> list[str]:
    """Dotted-module candidates an import could resolve to."""
    cands: list[str] = []
    if level == 0:
        if module:
            # `from a.b import c` -> try a.b.c then a.b
            for n in names:
                cands.append(f"{module}.{n}")
            cands.append(module)
        return cands

    # Relative import: base package = package_parts with (level-1) trimmed.
    pkg = _package_parts(rel_path)
    trim = level - 1
    base_parts = pkg[: len(pkg) - trim] if trim <= len(pkg) else []
    base = ".".join(base_parts)

    def _join(*bits: str) -> str:
        return ".".join(b for b in bits if b)

    if module:
        for n in names:
            cands.append(_join(base, module, n))
        cands.append(_join(base, module))
    else:
        for n in names:
            cands.append(_join(base, n))
        if base:
            cands.append(base)
    return [c for c in cands if c]


def resolve_edges(py_files: list[str], sources: dict[str, str]) -> set[tuple[str, str]]:
    """Return (importer, imported) file-path edges within the repo.

    `sources` maps file path -> source text.
    """
    index = build_module_index(py_files)
    edges: set[tuple[str, str]] = set()
    for rel in py_files:
        text = sources.get(rel)
        if text is None:
            continue
        for level, module, names in extract_imports(text):
            for cand in _candidates(rel, level, module, names):
                target = index.get(cand)
                if target and target != rel:
                    edges.add((rel, target))
                    break
    return edges


def analyze_imports(db: Session, analysis: Analysis, clone_path: str) -> dict:
    py_rows = db.scalars(
        select(FileMetric).where(
            FileMetric.analysis_id == analysis.id, FileMetric.language == "Python"
        )
    ).all()
    py_files = [r.file_path for r in py_rows]

    sources: dict[str, str] = {}
    for rel in py_files:
        try:
            with open(os.path.join(clone_path, rel), "r", encoding="utf-8", errors="replace") as fh:
                sources[rel] = fh.read()
        except OSError:
            continue

    edges = list(resolve_edges(py_files, sources))[:MAX_IMPORT_EDGES]
    db.bulk_save_objects(
        [
            FileConnection(
                analysis_id=analysis.id,
                source_file=src,
                target_file=dst,
                connection_type="import",
                weight=1,
            )
            for src, dst in edges
        ]
    )
    db.commit()
    return {"import_edges": len(edges), "python_files": len(py_files)}
