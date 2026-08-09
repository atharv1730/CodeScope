"""Repo cloning with basic resource guards.

Public deployment means we clone arbitrary user-supplied URLs, so we enforce a
timeout and a post-clone size ceiling. The clone lives in a per-analysis temp
directory that the caller is responsible for cleaning up.
"""
from __future__ import annotations

import os
import shutil

from git import GitCommandError, Repo

from app.config import settings


class CloneError(RuntimeError):
    """Raised when cloning fails or the repo violates a guard rail."""


def _dir_size_mb(path: str) -> float:
    total = 0
    for root, _dirs, files in os.walk(path):
        for f in files:
            fp = os.path.join(root, f)
            try:
                total += os.path.getsize(fp)
            except OSError:
                pass
    return total / (1024 * 1024)


def clone_repo(clone_url: str, analysis_id: str) -> str:
    """Clone `clone_url` into a fresh temp dir and return its path.

    Full history is cloned (no --depth) per project decision. GitPython honors
    the kill_after_timeout to abort a runaway clone.
    """
    dest = os.path.join(settings.clone_dir, analysis_id)
    if os.path.exists(dest):
        shutil.rmtree(dest, ignore_errors=True)
    os.makedirs(settings.clone_dir, exist_ok=True)

    try:
        Repo.clone_from(
            clone_url,
            dest,
            multi_options=["--no-single-branch"],
            kill_after_timeout=settings.clone_timeout_seconds,
        )
    except GitCommandError as exc:
        shutil.rmtree(dest, ignore_errors=True)
        raise CloneError(f"git clone failed: {exc.stderr or exc}") from exc

    size = _dir_size_mb(dest)
    if size > settings.max_repo_size_mb:
        shutil.rmtree(dest, ignore_errors=True)
        raise CloneError(
            f"Repository is {size:.0f} MB, exceeding the "
            f"{settings.max_repo_size_mb} MB limit."
        )

    return dest


def cleanup_clone(path: str) -> None:
    shutil.rmtree(path, ignore_errors=True)
