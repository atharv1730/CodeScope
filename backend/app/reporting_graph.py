"""Builders for the dependency-graph and dependency-health payloads (Day 4)."""
from __future__ import annotations

import os
from collections import Counter
from typing import Iterable

from app.models import Dependency, FileConnection, FileMetric

MAX_GRAPH_NODES = 400

# Filenames that typically mark an application entry point.
_ENTRY_BASENAMES = {
    "main.py", "__main__.py", "app.py", "manage.py", "wsgi.py", "asgi.py",
    "cli.py", "run.py", "server.py", "setup.py", "index.js", "server.js",
}
_CONFIG_BASENAMES = {
    "settings.py", "config.py", "conftest.py", "pyproject.toml", "package.json",
    "setup.cfg", "tox.ini",
}


def _is_entry(path: str) -> bool:
    return os.path.basename(path) in _ENTRY_BASENAMES


def _is_config(path: str) -> bool:
    return os.path.basename(path) in _CONFIG_BASENAMES


def build_graph_payload(
    file_metrics: Iterable[FileMetric], connections: Iterable[FileConnection]
) -> dict:
    imports = [c for c in connections if c.connection_type == "import"]
    metric_by_path = {m.file_path: m for m in file_metrics}

    # In-degree = how many files import this one (core files are imported a lot).
    in_degree: Counter[str] = Counter()
    for c in imports:
        in_degree[c.target_file] += 1

    node_paths: set[str] = set()
    for c in imports:
        node_paths.add(c.source_file)
        node_paths.add(c.target_file)

    # Rank nodes by importance so we can cap large graphs sensibly.
    ranked = sorted(node_paths, key=lambda p: in_degree.get(p, 0), reverse=True)
    kept = set(ranked[:MAX_GRAPH_NODES])

    nodes = []
    for path in kept:
        m = metric_by_path.get(path)
        nodes.append(
            {
                "id": path,
                "name": os.path.basename(path),
                "in_degree": in_degree.get(path, 0),
                "size": 1 + in_degree.get(path, 0),  # base size + importers
                "language": m.language if m else None,
                "lines_of_code": (m.lines_of_code if m else 0) or 0,
                "complexity_score": m.complexity_score if m else None,
                "change_frequency": (m.change_frequency if m else 0) or 0,
                "is_entry_point": _is_entry(path),
                "is_config": _is_config(path),
            }
        )

    edges = [
        {"source": c.source_file, "target": c.target_file}
        for c in imports
        if c.source_file in kept and c.target_file in kept
    ]

    entry_points = sorted(p for p in kept if _is_entry(p))

    return {
        "nodes": nodes,
        "edges": edges,
        "entry_points": entry_points,
        "summary": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "truncated": len(node_paths) > len(kept),
        },
    }


def build_dependencies_payload(dependencies: Iterable[Dependency]) -> dict:
    deps = list(dependencies)
    out = []
    for d in deps:
        details = d.vulnerability_details or {}
        out.append(
            {
                "name": d.name,
                "ecosystem": details.get("ecosystem"),
                "current_version": d.current_version,
                "latest_version": d.latest_version,
                "is_outdated": bool(d.is_outdated),
                "versions_behind": d.versions_behind or 0,
                "severely_outdated": (d.versions_behind or 0) > 2,
                "has_vulnerability": bool(d.has_vulnerability),
                "vulnerabilities": details.get("vulns", []),
                "source": details.get("source"),
            }
        )
    # Vulnerable first, then most out-of-date.
    out.sort(key=lambda d: (not d["has_vulnerability"], -d["versions_behind"]))

    return {
        "summary": {
            "total": len(out),
            "outdated": sum(1 for d in out if d["is_outdated"]),
            "severely_outdated": sum(1 for d in out if d["severely_outdated"]),
            "vulnerable": sum(1 for d in out if d["has_vulnerability"]),
        },
        "dependencies": out,
    }
