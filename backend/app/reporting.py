"""Transform stored file_metrics into API response payloads.

Kept separate from routers so the shaping logic is unit-testable without HTTP.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from app.models import FileMetric


def build_language_breakdown(metrics: Iterable[FileMetric]) -> list[dict]:
    agg: dict[str, dict] = defaultdict(lambda: {"files": 0, "lines_of_code": 0})
    for m in metrics:
        lang = m.language or "Unknown"
        agg[lang]["files"] += 1
        agg[lang]["lines_of_code"] += m.lines_of_code or 0
    breakdown = [
        {"language": lang, "files": v["files"], "lines_of_code": v["lines_of_code"]}
        for lang, v in agg.items()
    ]
    breakdown.sort(key=lambda d: d["lines_of_code"], reverse=True)
    return breakdown


def build_treemap(metrics: Iterable[FileMetric]) -> dict:
    """Nested directory tree sized by lines_of_code, for a D3 treemap.

    Each node: {name, path, size (leaf only), language (leaf only), children}.
    Directory `size` is the sum of descendant sizes (filled bottom-up by D3,
    but we also aggregate here so the payload is usable directly).
    """
    root: dict = {"name": "", "path": "", "children": {}, "size": 0}

    for m in metrics:
        parts = m.file_path.split("/")
        node = root
        for i, part in enumerate(parts):
            is_leaf = i == len(parts) - 1
            if is_leaf:
                node["children"][part] = {
                    "name": part,
                    "path": m.file_path,
                    "size": m.lines_of_code or 0,
                    "language": m.language,
                    "change_frequency": m.change_frequency or 0,
                }
            else:
                child = node["children"].get(part)
                if child is None:
                    child = {
                        "name": part,
                        "path": "/".join(parts[: i + 1]),
                        "children": {},
                        "size": 0,
                    }
                    node["children"][part] = child
                node = child

    def _finalize(node: dict) -> dict:
        children = node.get("children")
        if children is None:  # leaf
            return node
        child_list = [_finalize(c) for c in children.values()]
        total = sum(c["size"] for c in child_list)
        return {
            "name": node["name"],
            "path": node["path"],
            "size": total,
            "children": child_list,
        }

    return _finalize(root)


def build_structure_payload(metrics: list[FileMetric]) -> dict:
    languages = build_language_breakdown(metrics)
    return {
        "total_files": len(metrics),
        "total_lines_of_code": sum(m.lines_of_code or 0 for m in metrics),
        "languages": languages,
        "treemap": build_treemap(metrics),
    }


def build_complexity_payload(metrics: list[FileMetric]) -> dict:
    scored = [m for m in metrics if m.complexity_score is not None]
    scored.sort(key=lambda m: m.complexity_score or 0, reverse=True)

    files = [
        {
            "file_path": m.file_path,
            "language": m.language,
            "complexity_score": m.complexity_score,
            "function_count": m.function_count or 0,
            "lines_of_code": m.lines_of_code or 0,
            "avg_complexity_per_function": (
                round((m.complexity_score or 0) / m.function_count, 2)
                if m.function_count
                else None
            ),
        }
        for m in scored
    ]

    heatmap = [
        {"file_path": m["file_path"], "complexity_score": m["complexity_score"]}
        for m in files
    ]

    scores = [m.complexity_score for m in scored if m.complexity_score is not None]
    summary = {
        "python_files_scored": len(scored),
        "max_complexity": max(scores) if scores else 0,
        "avg_complexity": round(sum(scores) / len(scores), 2) if scores else 0,
        "analyzable": len(scored) > 0,
    }

    return {"summary": summary, "files": files, "heatmap": heatmap}
