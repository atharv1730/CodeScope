"""Parse `git log --numstat` output into structured history data.

Kept as a pure parser (string in, dataclasses out) so it can be unit-tested
without a real repository. The git pass calls `run_git_log` to get the raw
string, then `parse_git_log` to structure it, then aggregates.

Design notes:
- Full history, no commit cap (per project decision). `COMMIT_LIMIT` is exposed
  so a cap becomes a one-line change if a huge repo ever needs it.
- Merge commits are excluded (`--no-merges`) so file-change attribution and
  contributor counts reflect actual authored work.
- Renames in numstat ("old => new", "dir/{a => b}/f") are normalized to the new
  path.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime

from git import Repo

# None = no cap (full history). Set to an int to cap most-recent N commits.
COMMIT_LIMIT: int | None = None

# Field/record separators baked into the pretty-format below.
_FS = "\x1f"  # between fields of a commit header
_RS = "\x1e"  # marks the start of a commit header line

_PRETTY = f"format:{_RS}%H{_FS}%an{_FS}%ae{_FS}%aI"

_RENAME_BRACE = re.compile(r"\{(?P<pre>.*?) => (?P<post>.*?)\}")


@dataclass
class Commit:
    sha: str
    author_name: str
    author_email: str
    date: datetime
    files: list[str] = field(default_factory=list)


def run_git_log(repo_path: str) -> str:
    """Return raw `git log --no-merges --numstat` output for the current branch."""
    repo = Repo(repo_path)
    args = ["--no-merges", "--numstat", f"--pretty={_PRETTY}"]
    if COMMIT_LIMIT is not None:
        args.append(f"-n{COMMIT_LIMIT}")
    return repo.git.log(*args)


def _normalize_rename(path: str) -> str:
    """Turn a numstat rename path into the resulting (new) path."""
    if "{" in path and "=>" in path:
        path = _RENAME_BRACE.sub(lambda m: m.group("post"), path)
        path = path.replace("//", "/")
    elif " => " in path:
        # Plain "old => new"
        path = path.split(" => ", 1)[1]
    return path.strip()


def parse_git_log(output: str) -> list[Commit]:
    commits: list[Commit] = []
    current: Commit | None = None

    for line in output.split("\n"):
        if not line:
            continue
        if line.startswith(_RS):
            header = line[len(_RS):]
            parts = header.split(_FS)
            if len(parts) != 4:
                current = None
                continue
            sha, name, email, iso = parts
            try:
                dt = datetime.fromisoformat(iso)
            except ValueError:
                dt = None  # type: ignore[assignment]
            current = Commit(sha=sha, author_name=name, author_email=email, date=dt)
            commits.append(current)
        else:
            # numstat line: "added\tdeleted\tpath" (added/deleted are "-" for binary)
            if current is None:
                continue
            cols = line.split("\t")
            if len(cols) != 3:
                continue
            path = _normalize_rename(cols[2])
            if path:
                current.files.append(path)

    return commits
