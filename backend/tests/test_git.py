"""Tests for git-log parsing and contributor/hotspot builders."""
from datetime import date, datetime, timezone
from types import SimpleNamespace

from app.analysis.gitlog import _normalize_rename, parse_git_log
from app.reporting_git import build_contributors_payload, build_hotspots_payload

_RS = "\x1e"
_FS = "\x1f"


def _log(*commits) -> str:
    """Build a fake `git log --numstat` string. Each commit: (sha,name,email,iso,[(a,d,path)...])."""
    lines = []
    for sha, name, email, iso, files in commits:
        lines.append(f"{_RS}{sha}{_FS}{name}{_FS}{email}{_FS}{iso}")
        for a, d, path in files:
            lines.append(f"{a}\t{d}\t{path}")
    return "\n".join(lines)


def test_normalize_rename():
    assert _normalize_rename("old.py => new.py") == "new.py"
    assert _normalize_rename("src/{old => new}/file.py") == "src/new/file.py"
    assert _normalize_rename("a/b.py") == "a/b.py"


def test_parse_basic():
    out = _log(
        ("h1", "Ann", "ann@x.io", "2026-01-01T10:00:00+00:00",
         [("3", "1", "a.py"), ("2", "0", "b.py")]),
        ("h2", "Bob", "bob@x.io", "2026-01-02T10:00:00+00:00",
         [("1", "1", "a.py")]),
    )
    commits = parse_git_log(out)
    assert len(commits) == 2
    assert commits[0].author_name == "Ann"
    assert commits[0].files == ["a.py", "b.py"]
    assert commits[1].files == ["a.py"]


def test_parse_handles_binary_and_rename():
    out = _log(
        ("h1", "Ann", "ann@x.io", "2026-01-01T10:00:00+00:00",
         [("-", "-", "img.png"), ("4", "0", "pkg/{old => new}/m.py")]),
    )
    commits = parse_git_log(out)
    assert commits[0].files == ["img.png", "pkg/new/m.py"]


def _contrib(name, email, commits, last_days_ago):
    last = datetime.now(timezone.utc)
    last = last.replace(microsecond=0)
    from datetime import timedelta
    return SimpleNamespace(
        name=name, email=email, commit_count=commits,
        files_touched=commits, first_commit=last - timedelta(days=400),
        last_commit=last - timedelta(days=last_days_ago),
    )


def _fm(path, change, complexity=None, bus=2, top="Ann"):
    return SimpleNamespace(
        file_path=path, change_frequency=change, complexity_score=complexity,
        bus_factor=bus, top_contributor=top, last_changed=None,
    )


def test_contributors_payload_activity_and_warnings():
    contribs = [_contrib("Ann", "ann@x.io", 50, 5), _contrib("Bob", "bob@x.io", 10, 200)]
    activity = [
        SimpleNamespace(week_start=date(2026, 1, 5), author_email="ann@x.io", commit_count=3),
        SimpleNamespace(week_start=date(2026, 1, 12), author_email="ann@x.io", commit_count=2),
    ]
    fms = [_fm("solo.py", 12, bus=1, top="Ann"), _fm("shared.py", 8, bus=3)]
    out = build_contributors_payload(contribs, activity, fms)
    assert out["summary"]["contributor_count"] == 2
    assert out["summary"]["commit_count"] == 60
    assert out["summary"]["active_30"] == 1          # only Ann within 30d
    assert out["contributors"][0]["name"] == "Ann"   # sorted by commits
    assert len(out["timeline"]) == 2
    assert out["bus_factor_warnings"][0]["file_path"] == "solo.py"  # bus_factor==1


def test_hotspots_payload_churn_and_cochange():
    fms = [
        _fm("hot.py", 20, complexity=15.0),   # churn = 300
        _fm("calm.py", 2, complexity=3.0),    # churn = 6
        _fm("doc.md", 30, complexity=None),   # no complexity -> excluded from churn
    ]
    conns = [
        SimpleNamespace(connection_type="co_change", source_file="a.py",
                        target_file="b.py", weight=9),
        SimpleNamespace(connection_type="import", source_file="x.py",
                        target_file="y.py", weight=1),
    ]
    out = build_hotspots_payload(fms, conns)
    assert out["most_changed"][0]["file_path"] == "doc.md"   # highest change freq
    assert out["churn"][0]["file_path"] == "hot.py"          # highest churn
    assert out["churn"][0]["churn_score"] == 300.0
    assert all(c["file_path"] != "doc.md" for c in out["churn"])
    assert len(out["co_change"]) == 1                        # import excluded
    assert out["co_change"][0]["shared_commits"] == 9
