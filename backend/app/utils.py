"""Shared helpers: GitHub URL validation and status-to-progress mapping."""
from __future__ import annotations

import re

from app.models import AnalysisStatus

# Accept https/http github URLs, optionally ending in .git, optionally with
# trailing slash. Owner/repo segments only (no deep paths, tree/blob, etc.).
_GITHUB_RE = re.compile(
    r"^https?://github\.com/"
    r"(?P<owner>[A-Za-z0-9_.-]+)/"
    r"(?P<repo>[A-Za-z0-9_.-]+?)"
    r"(?:\.git)?/?$"
)


class InvalidRepoURL(ValueError):
    """Raised when a submitted URL is not an acceptable GitHub repo URL."""


def validate_github_url(url: str) -> tuple[str, str]:
    """Return (normalized_clone_url, repo_name) or raise InvalidRepoURL."""
    if not url:
        raise InvalidRepoURL("Repository URL is required.")
    match = _GITHUB_RE.match(url.strip())
    if not match:
        raise InvalidRepoURL(
            "Must be a public GitHub repository URL like "
            "https://github.com/owner/repo"
        )
    owner = match.group("owner")
    repo = match.group("repo")
    if repo.endswith(".git"):
        repo = repo[:-4]
    clone_url = f"https://github.com/{owner}/{repo}.git"
    repo_name = f"{owner}/{repo}"
    return clone_url, repo_name


# Rough progress percentages keyed by pipeline stage, for the polling UI.
_PROGRESS: dict[AnalysisStatus, int] = {
    AnalysisStatus.queued: 0,
    AnalysisStatus.cloning: 15,
    AnalysisStatus.analyzing_structure: 35,
    AnalysisStatus.analyzing_git: 55,
    AnalysisStatus.analyzing_complexity: 75,
    AnalysisStatus.analyzing_dependencies: 90,
    AnalysisStatus.complete: 100,
    AnalysisStatus.failed: 100,
}


def progress_for(status: AnalysisStatus) -> int:
    return _PROGRESS.get(status, 0)
