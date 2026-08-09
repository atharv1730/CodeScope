"""Git history pass: contributors, change frequency, bus factor, co-change.

Reads full history via `gitlog`, aggregates in memory, then persists:
- contributors        -> commits, first/last dates, files touched
- file_metrics        -> change_frequency, last_changed, top_contributor, bus_factor
- file_connections    -> co_change pairs (weight = shared-commit count)
- commit_activity     -> weekly commit counts per contributor
- analyses            -> commit_count, contributor_count
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, timedelta
from itertools import combinations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analysis.gitlog import parse_git_log, run_git_log
from app.models import Analysis, CommitActivity, Contributor, FileConnection, FileMetric

# Two files must co-occur in at least this many commits to count as coupled.
CO_CHANGE_MIN = 3
# Commits touching more files than this are skipped for co-change (bulk
# refactors / initial imports create noise, not real coupling). They still
# count toward change frequency and contributor stats.
MAX_FILES_FOR_COCHANGE = 40
# Cap stored co-change edges so the graph payload stays reasonable.
MAX_CO_CHANGE_EDGES = 500


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())  # Monday


def analyze_git(db: Session, analysis: Analysis, clone_path: str) -> dict:
    commits = parse_git_log(run_git_log(clone_path))

    # --- aggregate ---
    contrib_commits: Counter[str] = Counter()             # email -> commits
    contrib_name: dict[str, str] = {}                     # email -> display name
    contrib_first: dict[str, object] = {}
    contrib_last: dict[str, object] = {}
    contrib_files: dict[str, set[str]] = defaultdict(set)

    file_changes: Counter[str] = Counter()                # path -> commit count
    file_last: dict[str, object] = {}                     # path -> latest datetime
    file_authors: dict[str, Counter] = defaultdict(Counter)  # path -> email -> count
    co_change: Counter[tuple[str, str]] = Counter()       # (a,b) sorted -> count
    weekly: Counter[tuple[date, str]] = Counter()         # (week, email) -> commits

    for c in commits:
        email = c.author_email or "unknown"
        contrib_commits[email] += 1
        contrib_name.setdefault(email, c.author_name or email)
        if c.date is not None:
            if email not in contrib_first or c.date < contrib_first[email]:
                contrib_first[email] = c.date
            if email not in contrib_last or c.date > contrib_last[email]:
                contrib_last[email] = c.date
            weekly[(_week_start(c.date.date()), email)] += 1

        for path in c.files:
            file_changes[path] += 1
            contrib_files[email].add(path)
            file_authors[path][email] += 1
            if c.date is not None and (path not in file_last or c.date > file_last[path]):
                file_last[path] = c.date

        if 2 <= len(c.files) <= MAX_FILES_FOR_COCHANGE:
            for a, b in combinations(sorted(set(c.files)), 2):
                co_change[(a, b)] += 1

    # --- persist: file_metrics updates ---
    rows = db.scalars(
        select(FileMetric).where(FileMetric.analysis_id == analysis.id)
    ).all()
    existing_paths = set()
    for row in rows:
        existing_paths.add(row.file_path)
        row.change_frequency = file_changes.get(row.file_path, 0)
        row.last_changed = file_last.get(row.file_path)
        authors = file_authors.get(row.file_path)
        if authors:
            top_email, _ = authors.most_common(1)[0]
            row.top_contributor = contrib_name.get(top_email, top_email)
            row.bus_factor = len(authors)

    # --- persist: contributors ---
    contributor_rows = [
        Contributor(
            analysis_id=analysis.id,
            name=contrib_name.get(email, email),
            email=email,
            commit_count=count,
            first_commit=contrib_first.get(email),
            last_commit=contrib_last.get(email),
            files_touched=len(contrib_files.get(email, ())),
        )
        for email, count in contrib_commits.items()
    ]
    db.bulk_save_objects(contributor_rows)

    # --- persist: co-change edges (only between files still present) ---
    edges = [
        (a, b, n)
        for (a, b), n in co_change.most_common()
        if n >= CO_CHANGE_MIN and a in existing_paths and b in existing_paths
    ][:MAX_CO_CHANGE_EDGES]
    db.bulk_save_objects(
        [
            FileConnection(
                analysis_id=analysis.id,
                source_file=a,
                target_file=b,
                connection_type="co_change",
                weight=n,
            )
            for a, b, n in edges
        ]
    )

    # --- persist: weekly activity ---
    db.bulk_save_objects(
        [
            CommitActivity(
                analysis_id=analysis.id,
                week_start=week,
                author_email=email,
                author_name=contrib_name.get(email, email),
                commit_count=n,
            )
            for (week, email), n in weekly.items()
        ]
    )

    # --- persist: analysis summary ---
    analysis.commit_count = len(commits)
    analysis.contributor_count = len(contrib_commits)
    db.commit()

    return {
        "commits": len(commits),
        "contributors": len(contrib_commits),
        "co_change_edges": len(edges),
    }
