"""Detect and parse dependency manifests into a normalized requirement list.

Supported: requirements.txt (pip), pyproject.toml ([project] + poetry),
package.json (npm). Parsing is pure text/JSON/TOML work — no network — so it is
fully unit-testable.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None  # type: ignore[assignment]

# Manifest filenames we look for anywhere in the tree (shallow preference for
# repo root is handled by the caller ordering).
MANIFEST_FILENAMES = ("requirements.txt", "pyproject.toml", "package.json")

_PIP_NAME_RE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")
_PIP_PIN_RE = re.compile(r"==\s*([0-9][^,;\s]*)")


@dataclass
class Requirement:
    ecosystem: str  # "pypi" or "npm"
    name: str
    current_version: str | None  # concrete/declared version, if determinable
    source: str  # manifest file it came from (repo-relative)


def _parse_requirements_txt(text: str, source: str) -> list[Requirement]:
    reqs: list[Requirement] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("-"):  # -r, -e, --hash, options
            continue
        if line.startswith(("git+", "http://", "https://", "file:")):
            continue
        # Drop environment markers and inline comments.
        line = line.split(";", 1)[0].split(" #", 1)[0].strip()
        name_match = _PIP_NAME_RE.match(line)
        if not name_match:
            continue
        name = name_match.group(1)
        pin = _PIP_PIN_RE.search(line)
        version = pin.group(1) if pin else None
        reqs.append(Requirement("pypi", name, version, source))
    return reqs


def _parse_pyproject(text: str, source: str) -> list[Requirement]:
    if tomllib is None:
        return []
    try:
        data = tomllib.loads(text)
    except Exception:  # noqa: BLE001 - malformed toml
        return []

    reqs: list[Requirement] = []

    # PEP 621 [project].dependencies: list of PEP 508 strings.
    project = data.get("project", {})
    for dep in project.get("dependencies", []) or []:
        if isinstance(dep, str):
            reqs.extend(_parse_requirements_txt(dep, source))

    # Poetry [tool.poetry.dependencies]: table name -> constraint.
    poetry = data.get("tool", {}).get("poetry", {})
    for section in ("dependencies", "dev-dependencies"):
        table = poetry.get(section, {}) or {}
        for name, constraint in table.items():
            if name.lower() == "python":
                continue
            version = None
            if isinstance(constraint, str):
                version = _clean_leading_version(constraint)
            elif isinstance(constraint, dict):
                version = _clean_leading_version(str(constraint.get("version", "")))
            reqs.append(Requirement("pypi", name, version or None, source))
    return reqs


def _parse_package_json(text: str, source: str) -> list[Requirement]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    reqs: list[Requirement] = []
    for section in ("dependencies", "devDependencies", "peerDependencies"):
        deps = data.get(section) or {}
        if not isinstance(deps, dict):
            continue
        for name, rng in deps.items():
            version = _clean_leading_version(str(rng))
            reqs.append(Requirement("npm", name, version or None, source))
    return reqs


def _clean_leading_version(spec: str) -> str | None:
    """Pull a concrete-looking version out of an npm/poetry constraint."""
    spec = spec.strip()
    if not spec or spec in ("*", "latest") or spec.startswith(("git", "http", "file", "workspace")):
        return None
    m = re.search(r"([0-9]+(?:\.[0-9]+){0,2}(?:[.-][0-9A-Za-z]+)*)", spec)
    return m.group(1) if m else None


_PARSERS = {
    "requirements.txt": _parse_requirements_txt,
    "pyproject.toml": _parse_pyproject,
    "package.json": _parse_package_json,
}


def parse_manifest(filename: str, text: str, source: str) -> list[Requirement]:
    parser = _PARSERS.get(filename)
    return parser(text, source) if parser else []


def find_manifests(root: str, max_depth: int = 2) -> list[tuple[str, str]]:
    """Return (filename, abs_path) for manifests within `max_depth` dirs of root."""
    found: list[tuple[str, str]] = []
    root = os.path.abspath(root)
    for dirpath, dirnames, filenames in os.walk(root):
        depth = dirpath[len(root):].count(os.sep)
        if depth >= max_depth:
            dirnames[:] = []
        # Skip dependency install dirs.
        dirnames[:] = [d for d in dirnames if d not in {"node_modules", ".git", "vendor"}]
        for name in filenames:
            if name in MANIFEST_FILENAMES:
                found.append((name, os.path.join(dirpath, name)))
    return found
