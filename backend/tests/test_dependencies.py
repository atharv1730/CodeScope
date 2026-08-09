"""Tests for manifest parsing, version logic, import resolution, and builders."""
from types import SimpleNamespace

from app.analysis.imports import resolve_edges
from app.analysis.manifests import parse_manifest
from app.analysis.registry import summarize_vuln
from app.analysis.versions import is_outdated, is_severely_outdated, versions_behind
from app.reporting_graph import build_dependencies_payload, build_graph_payload


# --- manifest parsing ---

def test_parse_requirements_txt():
    text = (
        "# comment\n"
        "fastapi==0.115.0\n"
        "requests>=2.0  # inline\n"
        "uvicorn[standard]==0.30.6\n"
        "pkg ; python_version < '3.9'\n"
        "-r other.txt\n"
        "git+https://github.com/x/y.git\n"
    )
    reqs = parse_manifest("requirements.txt", text, "requirements.txt")
    names = {r.name: r.current_version for r in reqs}
    assert names["fastapi"] == "0.115.0"
    assert names["requests"] is None          # no pin
    assert names["uvicorn"] == "0.30.6"       # extras stripped
    assert "y" not in names and "other" not in names
    assert all(r.ecosystem == "pypi" for r in reqs)


def test_parse_package_json():
    text = '{"dependencies": {"react": "^18.2.0"}, "devDependencies": {"vite": "~5.0.0"}}'
    reqs = parse_manifest("package.json", text, "package.json")
    d = {r.name: r.current_version for r in reqs}
    assert d["react"] == "18.2.0"
    assert d["vite"] == "5.0.0"
    assert all(r.ecosystem == "npm" for r in reqs)


# --- version logic ---

def test_summarize_vuln_shapes():
    # severity as a top-level list (CVSS vector form)
    rec = {
        "id": "GHSA-xxxx",
        "summary": "XSS in template rendering",
        "severity": [{"type": "CVSS_V3", "score": "9.8"}],
        "aliases": ["CVE-2020-0001"],
    }
    out = summarize_vuln(rec)
    assert out["id"] == "GHSA-xxxx"
    assert out["severity"] == "9.8"
    assert out["aliases"] == ["CVE-2020-0001"]

    # no summary -> falls back to details; severity nested in database_specific
    rec2 = {
        "id": "PYSEC-1",
        "details": "A" * 500,
        "database_specific": {"severity": "HIGH"},
    }
    out2 = summarize_vuln(rec2)
    assert out2["summary"] and len(out2["summary"]) == 200
    assert out2["severity"] == "HIGH"


def test_version_helpers():
    assert is_outdated("1.2.3", "2.0.0") is True
    assert is_outdated("2.0.0", "2.0.0") is False
    assert versions_behind("1.5.0", "4.0.0") == 3
    assert is_severely_outdated("1.0.0", "4.0.0") is True   # >2 majors
    assert is_severely_outdated("3.0.0", "4.0.0") is False  # 1 major
    assert versions_behind("1.0.0", None) == 0              # unknown latest


# --- import resolution ---

def test_resolve_edges_absolute_and_relative():
    files = ["app/main.py", "app/util.py", "app/routers/__init__.py", "app/routers/health.py"]
    sources = {
        "app/main.py": "from app.util import helper\nfrom app.routers import health\n",
        "app/util.py": "import os\n",
        "app/routers/__init__.py": "",
        "app/routers/health.py": "from .. import util\n",
    }
    edges = resolve_edges(files, sources)
    assert ("app/main.py", "app/util.py") in edges
    assert ("app/main.py", "app/routers/health.py") in edges
    assert ("app/routers/health.py", "app/util.py") in edges
    # external import (os) creates no intra-repo edge
    assert all(dst != "os" for _, dst in edges)


# --- builders ---

def _dep(name, cur, latest, behind, vuln=False):
    return SimpleNamespace(
        name=name, current_version=cur, latest_version=latest,
        is_outdated=cur != latest, versions_behind=behind, has_vulnerability=vuln,
        vulnerability_details={"ecosystem": "pypi", "source": "requirements.txt",
                               "vulns": [{"id": "OSV-1"}] if vuln else []},
    )


def test_dependencies_payload_sorting_and_summary():
    deps = [
        _dep("safe", "2.0.0", "2.0.1", 0, vuln=False),
        _dep("old", "1.0.0", "5.0.0", 4, vuln=False),
        _dep("bad", "1.0.0", "1.2.0", 0, vuln=True),
    ]
    out = build_dependencies_payload(deps)
    assert out["summary"]["total"] == 3
    assert out["summary"]["vulnerable"] == 1
    assert out["summary"]["severely_outdated"] == 1
    assert out["dependencies"][0]["name"] == "bad"   # vulnerable sorts first


def _fm(path, lang="Python", loc=10, cx=None, change=0):
    return SimpleNamespace(
        file_path=path, language=lang, lines_of_code=loc, complexity_score=cx,
        change_frequency=change,
    )


def _conn(src, dst, ctype="import"):
    return SimpleNamespace(connection_type=ctype, source_file=src, target_file=dst, weight=1)


def test_graph_payload_indegree_and_entrypoints():
    fms = [_fm("app/main.py"), _fm("app/core.py"), _fm("app/util.py")]
    conns = [
        _conn("app/main.py", "app/core.py"),
        _conn("app/util.py", "app/core.py"),
        _conn("app/main.py", "app/util.py"),
    ]
    out = build_graph_payload(fms, conns)
    core = next(n for n in out["nodes"] if n["id"] == "app/core.py")
    assert core["in_degree"] == 2          # imported by main + util
    main = next(n for n in out["nodes"] if n["id"] == "app/main.py")
    assert main["is_entry_point"] is True
    assert "app/main.py" in out["entry_points"]
    assert out["summary"]["edge_count"] == 3
