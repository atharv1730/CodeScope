"""Unit tests for line counting, complexity, and reporting builders."""
from types import SimpleNamespace

from app.analysis.filereader import _count_python
from app.analysis.languages import count_lines_generic
from app.reporting import (
    build_complexity_payload,
    build_language_breakdown,
    build_treemap,
)


def _fm(path, language, loc, complexity=None, funcs=0, change=0):
    return SimpleNamespace(
        file_path=path,
        language=language,
        lines_of_code=loc,
        complexity_score=complexity,
        function_count=funcs,
        change_frequency=change,
    )


def test_python_line_counts():
    src = '"""module doc."""\n\nimport os  # inline\n\n\ndef f():\n    # a comment\n    return 1\n'
    counts = _count_python(src)
    assert counts.code >= 3
    assert counts.blank >= 2
    assert counts.comment >= 1
    assert counts.total == len(src.splitlines())


def test_generic_line_counts_js():
    src = "// header\nconst a = 1;\n\n/* block\n still */\nconst b = 2;\n"
    counts = count_lines_generic(src, "JavaScript")
    assert counts.code == 2      # the two const lines
    assert counts.blank == 1
    assert counts.comment == 3   # // + two block lines


def test_language_breakdown_sorted():
    metrics = [
        _fm("a.py", "Python", 100),
        _fm("b.py", "Python", 50),
        _fm("c.js", "JavaScript", 200),
    ]
    bd = build_language_breakdown(metrics)
    assert bd[0]["language"] == "JavaScript"  # 200 lines -> first
    assert bd[0]["files"] == 1
    py = next(x for x in bd if x["language"] == "Python")
    assert py["files"] == 2 and py["lines_of_code"] == 150


def test_treemap_nesting_and_sizes():
    metrics = [
        _fm("src/app/main.py", "Python", 10),
        _fm("src/app/util.py", "Python", 5),
        _fm("README.md", "Markdown", 3),
    ]
    tree = build_treemap(metrics)
    assert tree["size"] == 18
    names = {c["name"] for c in tree["children"]}
    assert {"src", "README.md"} <= names
    src = next(c for c in tree["children"] if c["name"] == "src")
    app = next(c for c in src["children"] if c["name"] == "app")
    assert app["size"] == 15


def test_complexity_payload_ranks_and_summarizes():
    metrics = [
        _fm("hard.py", "Python", 80, complexity=25.0, funcs=5),
        _fm("easy.py", "Python", 20, complexity=3.0, funcs=2),
        _fm("app.js", "JavaScript", 40, complexity=None),  # excluded
    ]
    payload = build_complexity_payload(metrics)
    assert payload["summary"]["python_files_scored"] == 2
    assert payload["summary"]["max_complexity"] == 25.0
    assert payload["files"][0]["file_path"] == "hard.py"  # ranked first
    assert payload["files"][0]["avg_complexity_per_function"] == 5.0
    assert all(f["file_path"] != "app.js" for f in payload["files"])
