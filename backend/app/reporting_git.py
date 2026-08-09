"""Builders for contributor and hotspot API payloads (Day 3).

Pure functions over ORM rows so they can be unit-tested without HTTP or a DB.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from app.models import CommitActivity, Contributor, FileConnection, FileMetric

# How many top contributors get their own timeline series.
TOP_CONTRIBUTOR_SERIES = 8
# List-length caps for payloads.
MAX_HOTSPOTS = 50
MAX_BUS_FACTOR_WARNINGS = 30
MAX_CO_CHANGE = 60


def _days_since(dt: datetime | None) -> int | None:
    if dt is None:
        return None
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (now - dt).days


def _activity_bucket(days: int | None) -> str:
    if days is None:
        return "unknown"
    if days <= 30:
        return "active_30"
    if days <= 60:
        return "active_60"
    if days <= 90:
        return "active_90"
    return "inactive"


def build_contributors_payload(
    contributors: Iterable[Contributor],
    activity: Iterable[CommitActivity],
    file_metrics: Iterable[FileMetric],
) -> dict:
    contribs = sorted(contributors, key=lambda c: c.commit_count or 0, reverse=True)

    people = []
    buckets = {"active_30": 0, "active_60": 0, "active_90": 0, "inactive": 0, "unknown": 0}
    for c in contribs:
        days = _days_since(c.last_commit)
        bucket = _activity_bucket(days)
        buckets[bucket] += 1
        people.append(
            {
                "name": c.name,
                "email": c.email,
                "commit_count": c.commit_count or 0,
                "files_touched": c.files_touched or 0,
                "first_commit": c.first_commit.isoformat() if c.first_commit else None,
                "last_commit": c.last_commit.isoformat() if c.last_commit else None,
                "days_since_last_commit": days,
                "activity": bucket,
            }
        )

    # Overall weekly timeline + per-contributor series for the top N.
    activity = list(activity)
    overall: dict[str, int] = {}
    for a in activity:
        key = a.week_start.isoformat()
        overall[key] = overall.get(key, 0) + (a.commit_count or 0)
    timeline = [{"week": w, "commits": n} for w, n in sorted(overall.items())]

    top_emails = {c.email for c in contribs[:TOP_CONTRIBUTOR_SERIES]}
    per_contrib: dict[str, dict[str, int]] = {}
    for a in activity:
        if a.author_email not in top_emails:
            continue
        per_contrib.setdefault(a.author_email, {})
        wk = a.week_start.isoformat()
        per_contrib[a.author_email][wk] = per_contrib[a.author_email].get(wk, 0) + (a.commit_count or 0)
    per_contributor_timeline = [
        {
            "email": email,
            "series": [{"week": w, "commits": n} for w, n in sorted(weeks.items())],
        }
        for email, weeks in per_contrib.items()
    ]

    # Single-owner risk: files touched, whose bus factor is 1.
    warnings = sorted(
        (
            m
            for m in file_metrics
            if (m.bus_factor or 0) == 1 and (m.change_frequency or 0) > 0
        ),
        key=lambda m: m.change_frequency or 0,
        reverse=True,
    )[:MAX_BUS_FACTOR_WARNINGS]
    bus_factor_warnings = [
        {
            "file_path": m.file_path,
            "bus_factor": m.bus_factor or 0,
            "change_frequency": m.change_frequency or 0,
            "owner": m.top_contributor,
        }
        for m in warnings
    ]

    return {
        "summary": {
            "contributor_count": len(contribs),
            "commit_count": sum(c.commit_count or 0 for c in contribs),
            "active_30": buckets["active_30"],
            "active_60": buckets["active_30"] + buckets["active_60"],
            "active_90": buckets["active_30"] + buckets["active_60"] + buckets["active_90"],
        },
        "contributors": people,
        "timeline": timeline,
        "per_contributor_timeline": per_contributor_timeline,
        "bus_factor_warnings": bus_factor_warnings,
    }


def build_hotspots_payload(
    file_metrics: Iterable[FileMetric],
    connections: Iterable[FileConnection],
) -> dict:
    metrics = list(file_metrics)

    most_changed = sorted(
        (m for m in metrics if (m.change_frequency or 0) > 0),
        key=lambda m: m.change_frequency or 0,
        reverse=True,
    )[:MAX_HOTSPOTS]
    most_changed_out = [
        {
            "file_path": m.file_path,
            "change_frequency": m.change_frequency or 0,
            "complexity_score": m.complexity_score,
            "last_changed": m.last_changed.isoformat() if m.last_changed else None,
            "top_contributor": m.top_contributor,
        }
        for m in most_changed
    ]

    # Churn = change frequency x complexity. High-churn + high-complexity files
    # are the most dangerous. Only Python files carry a complexity score.
    churn = [
        {
            "file_path": m.file_path,
            "change_frequency": m.change_frequency or 0,
            "complexity_score": m.complexity_score,
            "churn_score": round((m.change_frequency or 0) * m.complexity_score, 1),
        }
        for m in metrics
        if m.complexity_score is not None and (m.change_frequency or 0) > 0
    ]
    churn.sort(key=lambda d: d["churn_score"], reverse=True)
    churn = churn[:MAX_HOTSPOTS]

    co_change = sorted(
        (c for c in connections if c.connection_type == "co_change"),
        key=lambda c: c.weight or 0,
        reverse=True,
    )[:MAX_CO_CHANGE]
    co_change_out = [
        {"source_file": c.source_file, "target_file": c.target_file, "shared_commits": c.weight or 0}
        for c in co_change
    ]

    return {
        "most_changed": most_changed_out,
        "churn": churn,
        "co_change": co_change_out,
    }
