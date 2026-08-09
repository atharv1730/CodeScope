"""Dependency pass: parse manifests, check latest versions + known vulns.

Writes one `dependencies` row per unique (ecosystem, name). Network work is
done concurrently via `registry.fetch_all`; the pass degrades gracefully when a
registry is unreachable (latest/vuln fields simply stay empty).
"""
from __future__ import annotations

import asyncio
import os

from sqlalchemy.orm import Session

from app.analysis.manifests import Requirement, find_manifests, parse_manifest
from app.analysis.registry import fetch_all
from app.analysis.versions import is_outdated, versions_behind
from app.models import Analysis, Dependency

# Guard rail: skip pathological manifests (generated lockfiles etc.).
MAX_DEPENDENCIES = 400


def _collect_requirements(clone_path: str) -> list[Requirement]:
    seen: dict[tuple[str, str], Requirement] = {}
    for filename, abs_path in find_manifests(clone_path):
        try:
            with open(abs_path, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue
        source = os.path.relpath(abs_path, clone_path)
        for req in parse_manifest(filename, text, source):
            key = (req.ecosystem, req.name.lower())
            # First occurrence wins; prefer one that carries a version.
            if key not in seen or (seen[key].current_version is None and req.current_version):
                seen[key] = req
    return list(seen.values())[:MAX_DEPENDENCIES]


def analyze_dependencies(db: Session, analysis: Analysis, clone_path: str) -> dict:
    requirements = _collect_requirements(clone_path)
    if not requirements:
        return {"dependencies": 0, "outdated": 0, "vulnerable": 0}

    items = [(r.ecosystem, r.name, r.current_version) for r in requirements]
    results = asyncio.run(fetch_all(items))

    rows: list[Dependency] = []
    outdated_count = 0
    vulnerable_count = 0
    for req, res in zip(requirements, results):
        latest = res.latest_version
        outdated = is_outdated(req.current_version, latest)
        behind = versions_behind(req.current_version, latest)
        has_vuln = len(res.vulnerabilities) > 0
        if outdated:
            outdated_count += 1
        if has_vuln:
            vulnerable_count += 1
        rows.append(
            Dependency(
                analysis_id=analysis.id,
                name=req.name,
                current_version=req.current_version,
                latest_version=latest,
                is_outdated=outdated,
                versions_behind=behind,
                has_vulnerability=has_vuln,
                vulnerability_details={
                    "ecosystem": req.ecosystem,
                    "source": req.source,
                    "vulns": res.vulnerabilities,
                }
                if has_vuln
                else {"ecosystem": req.ecosystem, "source": req.source},
            )
        )

    db.bulk_save_objects(rows)
    db.commit()
    return {
        "dependencies": len(rows),
        "outdated": outdated_count,
        "vulnerable": vulnerable_count,
    }
